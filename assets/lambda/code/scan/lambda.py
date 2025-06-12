# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import glob
import json
import os
import pwd
import shutil
import subprocess
import time
from urllib.parse import unquote_plus

import boto3
import botocore
from aws_lambda_powertools import Logger, Metrics

logger = Logger()
metrics = Metrics()

s3_resource = boto3.resource("s3")
s3_client = boto3.client("s3")

INPROGRESS = "IN PROGRESS"
CLEAN = "CLEAN"
DELETED = "DELETED"
INFECTED = "INFECTED"
ERROR = "ERROR"
SKIP = "N/A"

MAX_BYTES = 4000000000


class ClamAVException(Exception):
    """Raise when ClamAV returns an unexpected exit code"""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


class ArchiveException(Exception):
    """Raise when 7za exits with an unexpected code"""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


class FileTooBigException(Exception):
    """Raise when file(s) is/are too large for ClamAV to scan"""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    logger.info(json.dumps(event))
    bucket_info = event["Records"][0]["s3"]
    input_bucket = bucket_info["bucket"]["name"]
    input_key = unquote_plus(bucket_info["object"]["key"])

    # Get version ID if object is versioned
    version_id = bucket_info["object"].get("versionId", None)
    version_id = None if version_id == "null" else version_id
    logger.info(
        f"Object versioning status: {'Versioned' if version_id else 'Not versioned'}"
    )

    if input_key.endswith("/"):
        summary = {
            "source": "serverless-clamscan",
            "input_bucket": input_bucket,
            "input_key": input_key,
            "status": SKIP,
            "message": "S3 Event trigger was for a non-file object",
        }
    elif (status := get_status(input_bucket, input_key, version_id)) == SKIP:
        summary = {
            "source": "serverless-clamscan",
            "input_bucket": input_bucket,
            "input_key": input_key,
            "status": status,
            "message": "S3 Event trigger was for a file already marked to skip",
        }
    elif status == DELETED:
        summary = {
            "source": "serverless-clamscan",
            "input_bucket": input_bucket,
            "input_key": input_key,
            "status": status,
            "message": "S3 Event trigger was for a file that has been deleted",
        }
    else:
        mount_path = os.environ["EFS_MOUNT_PATH"]
        definitions_path = f"{mount_path}/{os.environ['EFS_DEF_PATH']}"
        payload_path = f"{mount_path}/{context.aws_request_id}"
        tmp_path = f"{payload_path}-tmp"
        set_status(input_bucket, input_key, INPROGRESS, version_id)
        create_dir(input_bucket, input_key, payload_path)
        create_dir(input_bucket, input_key, tmp_path)
        download_object(input_bucket, input_key, payload_path, version_id)
        expand_if_large_archive(
            input_bucket,
            input_key,
            payload_path,
            bucket_info["object"]["size"],
        )
        create_dir(input_bucket, input_key, definitions_path)
        freshclam_update(
            input_bucket, input_key, payload_path, definitions_path
        )
        summary = scan(
            input_bucket,
            input_key,
            payload_path,
            definitions_path,
            tmp_path,
            version_id,
        )
        delete(payload_path)
        delete(tmp_path)

    # Add version ID to summary if object is versioned
    if version_id:
        summary["version_id"] = version_id

    logger.info(summary)
    return summary


def set_status(bucket, key, status, version_id=None):
    """Set the scan-status tag of the S3 Object"""
    logger.info(
        f"Attempting to set scan-status of {key} to {status}{' for version ' + version_id if version_id else ''}"
    )
    old_tags = {}
    try:
        if version_id:
            response = s3_client.get_object_tagging(
                Bucket=bucket, Key=key, VersionId=version_id
            )
        else:
            response = s3_client.get_object_tagging(Bucket=bucket, Key=key)
        old_tags = {i["Key"]: i["Value"] for i in response["TagSet"]}
    except botocore.exceptions.ClientError as e:
        logger.debug(e.response["Error"]["Message"])
    new_tags = {"scan-status": status}
    tags = {**old_tags, **new_tags}

    tagging_args = {
        "Bucket": bucket,
        "Key": key,
        "Tagging": {
            "TagSet": [
                {"Key": str(k), "Value": str(v)} for k, v in tags.items()
            ]
        },
    }

    if version_id:
        tagging_args["VersionId"] = version_id

    s3_client.put_object_tagging(**tagging_args)
    metrics.add_metric(name=status, unit="Count", value=1)


def get_status(bucket_name, object_key, version_id=None):
    """
    Retrieve the value of the status tag from an S3 object.

    Parameters:
        bucket_name (str): Name of the S3 bucket.
        object_key (str): The key (path) of the S3 object.
        version_id (str, optional): The version ID of the object if versioning is enabled.

    Returns:
        str: The value of the scan-status tag if found
        None: If the tag is not found
        "DELETED": If the object no longer exists
    """

    try:
        return get_tag_value(
            bucket_name, object_key, "scan-status", version_id
        )
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "NoSuchKey" or error_code == "404":
            logger.info(
                f"Object {object_key} in bucket {bucket_name}{' with version ' + version_id if version_id else ''} does not exist or has been deleted"
            )
            return "DELETED"
        else:
            logger.warning(
                "Error retrieving status: %s", e.response["Error"]["Message"]
            )
            return None


def get_tag_value(bucket_name, object_key, tag_key, version_id=None):
    """
    Retrieve the value of a specific tag from an S3 object.

    Parameters:
        bucket_name (str): Name of the S3 bucket.
        object_key (str): The key (path) of the S3 object.
        tag_key (str): The tag key to search for.
        version_id (str, optional): The version ID of the object if versioning is enabled.

    Returns:
        str: The value of the specified tag if found, else None.
    """
    # Retrieve the tagging information for the object.
    tagging_args = {"Bucket": bucket_name, "Key": object_key}

    if version_id:
        tagging_args["VersionId"] = version_id

    response = s3_client.get_object_tagging(**tagging_args)
    tag_set = response.get("TagSet", [])

    # Search for the specified tag_key in the returned tags.
    for tag in tag_set:
        if tag.get("Key") == tag_key:
            return tag.get("Value")
    # Return None if the tag_key wasn't found.
    return None


def create_dir(input_bucket, input_key, download_path):
    """Creates a directory at the specified location
    if it does not already exist"""
    sub_dir = os.path.dirname(input_key)
    full_path = download_path
    if len(sub_dir) > 0:
        full_path = os.path.join(full_path, sub_dir)
    logger.info(
        f"Attempting to create the EFS filepath {full_path} if it does not already exist"
    )
    if not os.path.exists(full_path):
        try:
            os.makedirs(full_path, exist_ok=True)
        except OSError as e:
            report_failure(input_bucket, input_key, download_path, str(e))


def download_object(input_bucket, input_key, download_path, version_id=None):
    """Downloads the specified file from S3 to EFS"""
    logger.info(
        f"Attempting to download of {input_key} from the {input_bucket} S3 Bucket{' version ' + version_id if version_id else ''} to the EFS filepath {download_path}"
    )
    try:
        download_args = {
            "Bucket": input_bucket,
            "Key": input_key,
            "Filename": f"{download_path}/{input_key}",
        }

        if version_id:
            download_args["VersionId"] = version_id

        s3_client.download_file(**download_args)
    except botocore.exceptions.ClientError as e:
        report_failure(
            input_bucket,
            input_key,
            download_path,
            e.response["Error"]["Message"],
            version_id,
        )


def expand_if_large_archive(input_bucket, input_key, download_path, byte_size):
    """Expand the file if it is an archival type and larger than ClamAV Max Size"""
    if byte_size > MAX_BYTES:
        logger.info(
            f"Attempting to expand {input_key} since the filesize is {byte_size} "
            f"bytes, which is greater than the ClamAV per file max of {MAX_BYTES}"
        )
        file_name = f"{download_path}/{input_key}"
        try:
            command = ["7za", "x", "-y", f"{file_name}", f"-o{download_path}"]
            archive_summary = subprocess.run(
                command,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            )
            if archive_summary.returncode not in [0, 1]:
                raise ArchiveException(
                    f"7za exited with unexpected code: {archive_summary.returncode}."
                )
            delete(download_path, input_key)
            large_file_list = []
            for root, dirs, files in os.walk(download_path, topdown=False):
                for name in files:
                    size = os.path.getsize(os.path.join(root, name))
                    if size > MAX_BYTES:
                        large_file_list.append(name)
            if large_file_list:
                raise FileTooBigException(
                    f"Archive {input_key} contains files {large_file_list} "
                    f"which are at greater than ClamAV max of {MAX_BYTES} bytes"
                )
        except subprocess.CalledProcessError as e:
            report_failure(
                input_bucket, input_key, download_path, str(e.stderr)
            )
        except ArchiveException as e:
            report_failure(input_bucket, input_key, download_path, e.message)
        except FileTooBigException as e:
            report_failure(input_bucket, input_key, download_path, e.message)
    else:
        return


last_update_time = 0


def freshclam_update(input_bucket, input_key, download_path, definitions_path):
    """Points freshclam to the local database files and the S3 Definitions bucket.
    Creates the database path on EFS if it does not already exist"""
    global last_update_time
    current_time = time.time()
    elapsed_time = current_time - last_update_time
    if (
        elapsed_time >= 3600
    ):  # Update definitions only once per hour to improve performance
        logger.info(
            f"Attempting to update the virus database. Last update was at {last_update_time} "
            f"epoch time. Current time is {current_time}"
        )
        conf = "/tmp/freshclam.conf"
        # will already exist when Lambdas are running in same execution context
        if not os.path.exists(conf):
            with open(conf, "a") as f:
                f.write(f"\nPrivateMirror {os.environ['DEFS_URL']}")
        try:
            command = [
                "freshclam",
                f"--config-file={conf}",
                "--stdout",
                "-u",
                f"{pwd.getpwuid(os.getuid()).pw_name}",
                f"--datadir={definitions_path}",
            ]
            update_summary = subprocess.run(
                command,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            )
            if update_summary.returncode != 0:
                raise ClamAVException(
                    f"FreshClam exited with unexpected code: {update_summary.returncode}"
                    f"\nOutput: {update_summary.stdout.decode('utf-8')}"
                )
            last_update_time = current_time
        except subprocess.CalledProcessError as e:
            report_failure(
                input_bucket, input_key, download_path, str(e.stderr)
            )
        except ClamAVException as e:
            report_failure(input_bucket, input_key, download_path, e.message)


def scan(
    input_bucket,
    input_key,
    download_path,
    definitions_path,
    tmp_path,
    version_id=None,
):
    """Scans the object from S3"""
    logger.info(
        f"Attempting to scan the file {input_key} from the {input_bucket} S3 Bucket{' version ' + version_id if version_id else ''} located at the EFS path {download_path}"
    )
    try:
        command = [
            "clamscan",
            "-v",
            "--stdout",
            f"--max-filesize={MAX_BYTES}",
            f"--max-scansize={MAX_BYTES}",
            f"--database={definitions_path}",
            "-r",
            f"--tempdir={tmp_path}",
            f"{download_path}",
        ]
        scan_summary = subprocess.run(
            command,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )
        if scan_summary.returncode == 0:
            status = CLEAN
        elif scan_summary.returncode == 1:
            status = INFECTED
        else:
            raise ClamAVException(
                f"ClamAV exited with unexpected code: {scan_summary.returncode}."
                f"\nOutput: {scan_summary.stdout.decode('utf-8')}"
            )
        set_status(input_bucket, input_key, status, version_id)
        summary = {
            "source": "serverless-clamscan",
            "input_bucket": input_bucket,
            "input_key": input_key,
            "status": status,
            "message": scan_summary.stdout.decode("utf-8"),
        }
        if version_id:
            summary["version_id"] = version_id
        return summary
    except subprocess.CalledProcessError as e:
        report_failure(
            input_bucket, input_key, download_path, str(e.stderr), version_id
        )
        return None
    except ClamAVException as e:
        report_failure(
            input_bucket, input_key, download_path, e.message, version_id
        )
        return None


def delete(download_path, input_key=None):
    """Deletes the file/folder from the EFS File System"""
    logger.info(
        f"Attempting to delete the file located at the EFS path {download_path}"
    )
    if input_key:
        file = f"{download_path}/{input_key}"
        if os.path.exists(file):
            os.remove(file)
    else:
        for obj in glob.glob(os.path.join(download_path, "*")):
            if os.path.isdir(obj):
                shutil.rmtree(obj)
            else:
                os.remove(obj)
        # Remove the download_path folder itself
        shutil.rmtree(download_path)


def report_failure(
    input_bucket, input_key, download_path, message, version_id=None
):
    """Set the S3 object tag to ERROR if scan function fails"""
    set_status(input_bucket, input_key, ERROR, version_id)
    delete(download_path)
    exception_json = {
        "source": "serverless-clamscan",
        "input_bucket": input_bucket,
        "input_key": input_key,
        "status": ERROR,
        "message": message,
    }
    if version_id:
        exception_json["version_id"] = version_id
    logger.error(exception_json)
    raise Exception(json.dumps(exception_json))
