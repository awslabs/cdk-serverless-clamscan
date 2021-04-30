# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import boto3
import botocore
import json
import logging
import os
import pwd
import subprocess
from aws_lambda_powertools import Logger


logger = Logger()


s3_resource = boto3.resource("s3")


class ClamAVException(Exception):
    """Raise when ClamAV returns an unexpected exit code"""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    """Updates the cvd files in the S3 Bucket"""
    print(json.dumps(event))
    defs_bucket = s3_resource.Bucket(os.environ["DEFS_BUCKET"])
    download_path = "/tmp"
    download_s3_defs(download_path, defs_bucket)
    freshclam_update(download_path)
    upload_s3_defs(download_path, defs_bucket)


def download_s3_defs(download_path, defs_bucket):
    """download CVD and conf files from definitions bucket (if they exist)
    to compare against ClamAV database. Respect their hosting costs!"""
    try:
        files = ["bytecode.cvd", "daily.cvd", "main.cvd", "freshclam.conf"]
        for filename in files:
            defs_bucket.download_file(filename, f"{download_path}/{filename}")
    except botocore.exceptions.ClientError:
        pass


def upload_s3_defs(download_path, defs_bucket):
    """Upload CVD and DB files to definitions bucket"""
    try:
        for root, dirs, files in os.walk(download_path):
            for file in files:
                defs_bucket.upload_file(os.path.join(root, file), file)
    except botocore.exceptions.ClientError as e:
        msg = e.response["Error"]["Message"]
        logger.error(msg)
        report_failure(msg)


def freshclam_update(download_path):
    """Points freshclam to the local database files. Downloads
    the latest database files"""
    conf = "/tmp/freshclam.conf"
    # will already exist when Lambdas are running in same execution context
    # or downloaded from the Virus Defs bucket
    if not os.path.exists(conf):
        with open(conf, "a") as f:
            f.write("\nDNSDatabaseInfo current.cvd.clamav.net")
            f.write("\nDatabaseMirror  database.clamav.net")
    try:
        command = [
            "freshclam",
            f"--config-file={conf}",
            "--stdout",
            "-u",
            f"{pwd.getpwuid(os.getuid()).pw_name}",
            f"--datadir={download_path}",
        ]
        update_summary = subprocess.run(
            command,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )
        if update_summary.returncode != 0:
            raise ClamAVException(
                f"FreshClam exited with unexpected code: {update_summary.returncode}"
            )
    except subprocess.CalledProcessError as e:
        report_failure(str(e.stderr))
    except ClamAVException as e:
        report_failure(e.message)
    return


def report_failure(message):
    """ """
    exception_json = {
        "source": "serverless-clamscan-update",
        "message": message,
    }
    raise Exception(json.dumps(exception_json))
