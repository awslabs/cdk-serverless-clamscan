import subprocess
from unittest.mock import patch
import importlib
import tempfile
import os
import json

import botocore
import pytest
import boto3
from botocore.stub import Stubber
from assertpy import assert_that, add_extension

# lambda is a reserved keyword in Python, so this import must be done dynamically
scan_lambda = importlib.import_module("lambda")


# Add custom extensions to assertpy for boto3 stubber and mocks
def has_no_pending_responses(self):
    self.val.assert_no_pending_responses()
    return self


def is_called(self):
    self.val.assert_called()
    return self


def is_called_once(self):
    self.val.assert_called_once()
    return self


def is_called_with(self, *args, **kwargs):
    self.val.assert_called_with(*args, **kwargs)
    return self


# Register the custom extensions
add_extension(has_no_pending_responses)
add_extension(is_called)
add_extension(is_called_once)
add_extension(is_called_with)

# Get the original, undecorated lambda_handler function
original_handler = None
for attr_name in dir(scan_lambda.lambda_handler):
    if attr_name == "__wrapped__":
        original_handler = getattr(scan_lambda.lambda_handler, attr_name)
        # If we find another __wrapped__ attribute, we need to keep unwrapping
        while hasattr(original_handler, "__wrapped__"):
            original_handler = original_handler.__wrapped__

# If we couldn't unwrap the handler, just use the decorated one
if original_handler is None:
    original_handler = scan_lambda.lambda_handler


@pytest.fixture
def s3_event_versioned():
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {
                        "key": "test.txt",
                        "size": 123,
                        "versionId": "abc123",
                    },
                }
            }
        ]
    }


@pytest.fixture
def s3_event_unversioned():
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {
                        "key": "test.txt",
                        "size": 123,
                    },
                }
            }
        ]
    }


@pytest.fixture
def s3_stubber():
    """Create and return a Stubber for the S3 client"""
    # Create a new S3 client for each test
    s3_client = boto3.client("s3")
    with Stubber(s3_client) as stubber:
        # Replace the global s3_client in the lambda module with our stubbed client
        original_client = scan_lambda.s3_client
        scan_lambda.s3_client = s3_client
        yield stubber
        # Restore the original client after the test
        scan_lambda.s3_client = original_client


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up is handled by the delete mock in tests


class DummyContext:
    aws_request_id = "req-1"
    function_name = "test-function"
    memory_limit_in_mb = 512
    invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    )


def test_set_status_versioned(s3_stubber):
    # Arrange
    bucket = "bucket"
    key = "key"
    status = scan_lambda.ScanStatus.CLEAN
    version_id = "v1"

    # Stub the get_object_tagging call
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": []},
        {"Bucket": bucket, "Key": key, "VersionId": version_id},
    )

    # Stub the put_object_tagging call
    expected_tags = {"TagSet": [{"Key": "scan-status", "Value": status}]}
    s3_stubber.add_response(
        "put_object_tagging",
        {},
        {
            "Bucket": bucket,
            "Key": key,
            "Tagging": expected_tags,
            "VersionId": version_id,
        },
    )

    # Act
    scan_lambda.set_status(bucket, key, status, version_id=version_id)

    # Assert
    assert_that(s3_stubber).has_no_pending_responses()


def test_set_status_unversioned(s3_stubber):
    # Arrange
    bucket = "bucket"
    key = "key"
    status = scan_lambda.ScanStatus.CLEAN

    # Stub the get_object_tagging call
    s3_stubber.add_response(
        "get_object_tagging", {"TagSet": []}, {"Bucket": bucket, "Key": key}
    )

    # Stub the put_object_tagging call
    expected_tags = {"TagSet": [{"Key": "scan-status", "Value": status}]}
    s3_stubber.add_response(
        "put_object_tagging",
        {},
        {"Bucket": bucket, "Key": key, "Tagging": expected_tags},
    )

    # Act
    scan_lambda.set_status(bucket, key, status)

    # Assert
    assert_that(s3_stubber).has_no_pending_responses()


def test_get_status_versioned_found(s3_stubber):
    # Arrange
    expected_status = scan_lambda.ScanStatus.CLEAN
    bucket = "bucket"
    key = "key"
    version_id = "v1"

    # Stub the get_object_tagging call
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": [{"Key": "scan-status", "Value": expected_status}]},
        {"Bucket": bucket, "Key": key, "VersionId": version_id},
    )

    # Act
    status = scan_lambda.get_status(bucket, key, version_id=version_id)

    # Assert
    assert_that(status).is_equal_to(expected_status)
    assert_that(s3_stubber).has_no_pending_responses()


def test_get_status_unversioned_found(s3_stubber):
    # Arrange
    expected_status = scan_lambda.ScanStatus.CLEAN
    bucket = "bucket"
    key = "key"

    # Stub the get_object_tagging call
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": [{"Key": "scan-status", "Value": expected_status}]},
        {"Bucket": bucket, "Key": key},
    )

    # Act
    status = scan_lambda.get_status(bucket, key)

    # Assert
    assert_that(status).is_equal_to(expected_status)
    assert_that(s3_stubber).has_no_pending_responses()


def test_get_status_deleted(s3_stubber):
    # Arrange
    bucket = "bucket"
    key = "key"
    version_id = "v1"

    # Stub the get_object_tagging call with an error
    s3_stubber.add_client_error(
        "get_object_tagging",
        service_error_code="NoSuchKey",
        service_message="Not found",
        http_status_code=404,
        expected_params={
            "Bucket": bucket,
            "Key": key,
            "VersionId": version_id,
        },
    )

    # Act
    status = scan_lambda.get_status(bucket, key, version_id=version_id)

    # Assert
    assert_that(status).is_equal_to(scan_lambda.ScanStatus.DELETED)
    assert_that(s3_stubber).has_no_pending_responses()


def test_get_tag_value_versioned(s3_stubber):
    # Arrange
    expected_value = "bar"
    bucket = "bucket"
    key = "key"
    tag_key = "foo"
    version_id = "v1"

    # Stub the get_object_tagging call
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": [{"Key": "foo", "Value": expected_value}]},
        {"Bucket": bucket, "Key": key, "VersionId": version_id},
    )

    # Act
    value = scan_lambda.get_tag_value(
        bucket, key, tag_key, version_id=version_id
    )

    # Assert
    assert_that(value).is_equal_to(expected_value)
    assert_that(s3_stubber).has_no_pending_responses()


def test_get_tag_value_not_found(s3_stubber):
    # Arrange
    bucket = "bucket"
    key = "key"
    tag_key = "baz"  # Different from what's in the TagSet

    # Stub the get_object_tagging call
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": [{"Key": "foo", "Value": "bar"}]},
        {"Bucket": bucket, "Key": key},
    )

    # Act
    value = scan_lambda.get_tag_value(bucket, key, tag_key)

    # Assert
    assert_that(value).is_none()
    assert_that(s3_stubber).has_no_pending_responses()


@patch("lambda.create_dir")
@patch("lambda.download_object")
@patch("lambda.expand_if_large_archive")
@patch("lambda.freshclam_update")
@patch("lambda.scan", return_value={"status": scan_lambda.ScanStatus.CLEAN})
@patch("lambda.delete")
@patch("lambda.metrics")
def test_lambda_handler_versioned(
    mock_metrics,
    mock_delete,
    mock_scan,
    mock_freshclam,
    mock_expand,
    mock_download,
    mock_create,
    s3_stubber,
    s3_event_versioned,
    temp_dir,
):
    # Arrange
    ctx = DummyContext()
    expected_status = scan_lambda.ScanStatus.CLEAN
    env_vars = {
        "EFS_DEF_PATH": "defs",
        "EFS_MOUNT_PATH": tempfile.gettempdir(),
        "POWERTOOLS_METRICS_NAMESPACE": "test-namespace",
        "POWERTOOLS_SERVICE_NAME": "test-service",
    }

    # Disable metrics collection completely in tests
    # Create a mock that does nothing when these methods are called
    mock_metrics.log_metrics = lambda *args, **kwargs: lambda fn: fn
    mock_metrics.namespace = "test-namespace"
    mock_metrics.add_metric.return_value = None
    mock_metrics.flush_metrics.return_value = None
    mock_metrics.add_dimension.return_value = None

    # First, stub the get_object_tagging call for get_status
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": []},
        {"Bucket": "test-bucket", "Key": "test.txt", "VersionId": "abc123"},
    )

    # Second, stub the get_object_tagging call for set_status
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": []},
        {"Bucket": "test-bucket", "Key": "test.txt", "VersionId": "abc123"},
    )

    # Third, stub the put_object_tagging call for set_status
    s3_stubber.add_response(
        "put_object_tagging",
        {},
        {
            "Bucket": "test-bucket",
            "Key": "test.txt",
            "Tagging": {
                "TagSet": [
                    {
                        "Key": "scan-status",
                        "Value": scan_lambda.ScanStatus.IN_PROGRESS,
                    }
                ]
            },
            "VersionId": "abc123",
        },
    )

    # Act
    with patch.dict("os.environ", env_vars):
        result = original_handler(s3_event_versioned, ctx)

    # Assert
    assert_that(result).has_status(expected_status)
    assert_that(result).has_version_id("abc123")
    assert_that(mock_create).is_called()
    assert_that(mock_download).is_called()
    assert_that(mock_expand).is_called()
    assert_that(mock_freshclam).is_called()
    assert_that(mock_scan).is_called()
    assert_that(mock_delete).is_called()
    assert_that(s3_stubber).has_no_pending_responses()


@patch("lambda.create_dir")
@patch("lambda.download_object")
@patch("lambda.expand_if_large_archive")
@patch("lambda.freshclam_update")
@patch("lambda.scan", return_value={"status": scan_lambda.ScanStatus.CLEAN})
@patch("lambda.delete")
@patch("lambda.metrics")
def test_lambda_handler_unversioned(
    mock_metrics,
    mock_delete,
    mock_scan,
    mock_freshclam,
    mock_expand,
    mock_download,
    mock_create,
    s3_stubber,
    s3_event_unversioned,
    temp_dir,
):
    # Arrange
    ctx = DummyContext()
    expected_status = scan_lambda.ScanStatus.CLEAN
    env_vars = {
        "EFS_DEF_PATH": "defs",
        "EFS_MOUNT_PATH": tempfile.gettempdir(),
        "POWERTOOLS_METRICS_NAMESPACE": "test-namespace",
        "POWERTOOLS_SERVICE_NAME": "test-service",
    }

    # Disable metrics collection completely in tests
    # Create a mock that does nothing when these methods are called
    mock_metrics.log_metrics = lambda *args, **kwargs: lambda fn: fn
    mock_metrics.namespace = "test-namespace"
    mock_metrics.add_metric.return_value = None
    mock_metrics.flush_metrics.return_value = None
    mock_metrics.add_dimension.return_value = None

    # First, stub the get_object_tagging call for get_status
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": []},
        {"Bucket": "test-bucket", "Key": "test.txt"},
    )

    # Second, stub the get_object_tagging call for set_status
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": []},
        {"Bucket": "test-bucket", "Key": "test.txt"},
    )

    # Third, stub the put_object_tagging call for set_status
    s3_stubber.add_response(
        "put_object_tagging",
        {},
        {
            "Bucket": "test-bucket",
            "Key": "test.txt",
            "Tagging": {
                "TagSet": [
                    {
                        "Key": "scan-status",
                        "Value": scan_lambda.ScanStatus.IN_PROGRESS,
                    }
                ]
            },
        },
    )

    # Act
    with patch.dict("os.environ", env_vars):
        result = original_handler(s3_event_unversioned, ctx)

    # Assert
    assert_that(result).has_status(expected_status)
    assert_that(result).does_not_contain_key("version_id")
    assert_that(mock_create).is_called()
    assert_that(mock_download).is_called()
    assert_that(mock_expand).is_called()
    assert_that(mock_freshclam).is_called()
    assert_that(mock_scan).is_called()
    assert_that(mock_delete).is_called()
    assert_that(s3_stubber).has_no_pending_responses()


@patch("lambda.metrics.flush_metrics")
@patch("lambda.metrics.add_metric")
def test_lambda_handler_directory_path(mock_add_metric, mock_flush_metrics):
    # Arrange
    ctx = DummyContext()
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {
                        "key": "directory/",
                        "size": 0,
                    },
                }
            }
        ]
    }
    env_vars = {
        "EFS_DEF_PATH": "defs",
        "EFS_MOUNT_PATH": tempfile.gettempdir(),
        "POWERTOOLS_METRICS_NAMESPACE": "test-namespace",
        "POWERTOOLS_SERVICE_NAME": "test-service",
    }

    # Create a mock metrics object
    original_metrics = scan_lambda.metrics
    try:
        # Act
        with patch.dict("os.environ", env_vars):
            # Set namespace directly before the test
            scan_lambda.metrics.namespace = "test-namespace"
            result = scan_lambda.lambda_handler(event, ctx)
    finally:
        # Restore original metrics
        scan_lambda.metrics = original_metrics

    # Assert
    assert_that(result["status"]).is_equal_to(scan_lambda.ScanStatus.SKIP)
    assert_that(result["message"]).contains("non-file object")


@patch("lambda.metrics.flush_metrics")
@patch("lambda.metrics.add_metric")
def test_lambda_handler_skip_status(
    mock_add_metric, mock_flush_metrics, s3_stubber
):
    # Arrange
    ctx = DummyContext()
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {
                        "key": "test.txt",
                        "size": 123,
                    },
                }
            }
        ]
    }
    env_vars = {
        "EFS_DEF_PATH": "defs",
        "EFS_MOUNT_PATH": tempfile.gettempdir(),
        "POWERTOOLS_METRICS_NAMESPACE": "test-namespace",
        "POWERTOOLS_SERVICE_NAME": "test-service",
    }

    # Stub the get_object_tagging call for get_status
    s3_stubber.add_response(
        "get_object_tagging",
        {
            "TagSet": [
                {"Key": "scan-status", "Value": scan_lambda.ScanStatus.SKIP}
            ]
        },
        {"Bucket": "test-bucket", "Key": "test.txt"},
    )

    # Create a mock metrics object
    original_metrics = scan_lambda.metrics
    try:
        # Act
        with patch.dict("os.environ", env_vars):
            # Set namespace directly before the test
            scan_lambda.metrics.namespace = "test-namespace"
            result = scan_lambda.lambda_handler(event, ctx)
    finally:
        # Restore original metrics
        scan_lambda.metrics = original_metrics

    # Assert
    assert_that(result["status"]).is_equal_to(scan_lambda.ScanStatus.SKIP)
    assert_that(result["message"]).contains("already marked to skip")
    assert_that(s3_stubber).has_no_pending_responses()


@patch("lambda.metrics.flush_metrics")
@patch("lambda.metrics.add_metric")
def test_lambda_handler_deleted_status(
    mock_add_metric, mock_flush_metrics, s3_stubber
):
    # Arrange
    ctx = DummyContext()
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {
                        "key": "test.txt",
                        "size": 123,
                    },
                }
            }
        ]
    }
    env_vars = {
        "EFS_DEF_PATH": "defs",
        "EFS_MOUNT_PATH": tempfile.gettempdir(),
        "POWERTOOLS_METRICS_NAMESPACE": "test-namespace",
        "POWERTOOLS_SERVICE_NAME": "test-service",
    }

    # Stub the get_object_tagging call for get_status with an error
    s3_stubber.add_client_error(
        "get_object_tagging",
        service_error_code="NoSuchKey",
        service_message="Not found",
        http_status_code=404,
        expected_params={"Bucket": "test-bucket", "Key": "test.txt"},
    )

    # Create a mock metrics object
    original_metrics = scan_lambda.metrics
    try:
        # Act
        with patch.dict("os.environ", env_vars):
            # Set namespace directly before the test
            scan_lambda.metrics.namespace = "test-namespace"
            result = scan_lambda.lambda_handler(event, ctx)
    finally:
        # Restore original metrics
        scan_lambda.metrics = original_metrics

    # Assert
    assert_that(result["status"]).is_equal_to(scan_lambda.ScanStatus.DELETED)
    assert_that(result["message"]).contains("has been deleted")
    assert_that(s3_stubber).has_no_pending_responses()


@patch("os.path.exists")
def test_create_dir_already_exists(mock_exists):
    # Arrange
    mock_exists.return_value = True
    bucket = "test-bucket"
    key = "test.txt"
    download_path = tempfile.mkdtemp()

    # Act
    scan_lambda.create_dir(bucket, key, download_path)

    # Assert
    mock_exists.assert_called_once()


@patch("os.path.exists")
@patch("os.makedirs")
def test_create_dir_success(mock_makedirs, mock_exists):
    # Arrange
    mock_exists.return_value = False
    bucket = "test-bucket"
    key = "test.txt"
    download_path = tempfile.mkdtemp()

    # Act
    scan_lambda.create_dir(bucket, key, download_path)

    # Assert
    mock_exists.assert_called_once()
    mock_makedirs.assert_called_once_with(download_path, exist_ok=True)


@patch("os.path.exists")
@patch("os.makedirs")
@patch.object(scan_lambda, "report_failure")
def test_create_dir_error(mock_report_failure, mock_makedirs, mock_exists):
    # Arrange
    mock_exists.return_value = False
    mock_makedirs.side_effect = OSError("Test error")
    bucket = "test-bucket"
    key = "test.txt"
    download_path = tempfile.mkdtemp()

    # Act
    scan_lambda.create_dir(bucket, key, download_path)

    # Assert
    mock_exists.assert_called_once()
    mock_makedirs.assert_called_once_with(download_path, exist_ok=True)
    mock_report_failure.assert_called_once_with(
        bucket, key, download_path, "Test error"
    )


@patch.object(scan_lambda.s3_client, "download_file")
def test_download_object_success(mock_download_file):
    # Arrange
    bucket = "test-bucket"
    key = "test.txt"
    download_path = tempfile.mkdtemp()
    version_id = "v1"

    # Act
    scan_lambda.download_object(bucket, key, download_path, version_id)

    # Assert
    mock_download_file.assert_called_once_with(
        Bucket=bucket,
        Key=key,
        Filename=f"{download_path}/{key}",
        ExtraArgs={"VersionId": version_id},
    )


@patch.object(scan_lambda.s3_client, "download_file")
@patch.object(scan_lambda, "report_failure")
def test_download_object_error(mock_report_failure, mock_download_file):
    # Arrange
    bucket = "test-bucket"
    key = "test.txt"
    download_path = tempfile.mkdtemp()
    version_id = "v1"
    error_message = "Access Denied"
    mock_download_file.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Message": error_message}}, "download_file"
    )

    # Act
    scan_lambda.download_object(bucket, key, download_path, version_id)

    # Assert
    mock_download_file.assert_called_once()
    mock_report_failure.assert_called_once_with(
        bucket, key, download_path, error_message, version_id
    )


@patch("lambda.subprocess.run")
def test_scan_clean_result(mock_run, s3_stubber):
    # Arrange
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = (
        b"----------- SCAN SUMMARY -----------\nInfected files: 0\n"
    )
    input_bucket = "test-bucket"
    input_key = "test-file.txt"
    download_path = tempfile.mkdtemp()
    definitions_path = "/tmp/defs"
    tmp_path = "/tmp/tmp-path"
    version_id = "v1"

    # Stub the get_object_tagging call for set_status
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": []},
        {"Bucket": input_bucket, "Key": input_key, "VersionId": version_id},
    )

    # Stub the put_object_tagging call for set_status
    s3_stubber.add_response(
        "put_object_tagging",
        {},
        {
            "Bucket": input_bucket,
            "Key": input_key,
            "Tagging": {
                "TagSet": [
                    {
                        "Key": "scan-status",
                        "Value": scan_lambda.ScanStatus.CLEAN,
                    }
                ]
            },
            "VersionId": version_id,
        },
    )

    # Act
    with patch.object(scan_lambda.metrics, "add_metric"), patch.object(
        scan_lambda.metrics, "flush_metrics"
    ), patch.dict(
        "os.environ", {"POWERTOOLS_METRICS_NAMESPACE": "test-namespace"}
    ):
        result = scan_lambda.scan(
            input_bucket,
            input_key,
            download_path,
            definitions_path,
            tmp_path,
            version_id,
        )

    # Assert
    assert_that(result).is_not_none()
    assert_that(result["status"]).is_equal_to(scan_lambda.ScanStatus.CLEAN)
    assert_that(s3_stubber).has_no_pending_responses()


@patch("lambda.subprocess.run")
def test_scan_infected_result(mock_run, s3_stubber):
    # Arrange
    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = (
        b"----------- SCAN SUMMARY -----------\nInfected files: "
        b"1\n/tmp/path/test-file.txt: Eicar-Test-Signature FOUND\n"
    )
    input_bucket = "test-bucket"
    input_key = "test-file.txt"
    download_path = tempfile.mkdtemp()
    definitions_path = "/tmp/defs"
    tmp_path = "/tmp/tmp-path"
    version_id = "v1"

    # Stub the get_object_tagging call for set_status
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": []},
        {"Bucket": input_bucket, "Key": input_key, "VersionId": version_id},
    )

    # Stub the put_object_tagging call for set_status
    s3_stubber.add_response(
        "put_object_tagging",
        {},
        {
            "Bucket": input_bucket,
            "Key": input_key,
            "Tagging": {
                "TagSet": [
                    {
                        "Key": "scan-status",
                        "Value": scan_lambda.ScanStatus.INFECTED,
                    }
                ]
            },
            "VersionId": version_id,
        },
    )

    # Act
    with patch.object(scan_lambda.metrics, "add_metric"), patch.object(
        scan_lambda.metrics, "flush_metrics"
    ), patch.dict(
        "os.environ", {"POWERTOOLS_METRICS_NAMESPACE": "test-namespace"}
    ):
        result = scan_lambda.scan(
            input_bucket,
            input_key,
            download_path,
            definitions_path,
            tmp_path,
            version_id,
        )

    # Assert
    assert_that(result).is_not_none()
    assert_that(result["status"]).is_equal_to(scan_lambda.ScanStatus.INFECTED)
    assert_that(s3_stubber).has_no_pending_responses()


@patch("lambda.subprocess.run")
def test_scan_error_result(mock_run, s3_stubber):
    # Arrange
    mock_run.return_value.returncode = 2  # Error code
    mock_run.return_value.stdout = (
        b"----------- SCAN SUMMARY -----------\nError: Some error occurred\n"
    )
    input_bucket = "test-bucket"
    input_key = "test-file.txt"
    download_path = tempfile.mkdtemp()
    definitions_path = "/tmp/defs"
    tmp_path = "/tmp/tmp-path"

    # Stub the get_object_tagging call for set_status and report_failure
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": []},
        {"Bucket": input_bucket, "Key": input_key},
    )

    # Stub the put_object_tagging call for set_status and report_failure
    s3_stubber.add_response(
        "put_object_tagging",
        {},
        {
            "Bucket": input_bucket,
            "Key": input_key,
            "Tagging": {
                "TagSet": [
                    {
                        "Key": "scan-status",
                        "Value": scan_lambda.ScanStatus.ERROR,
                    }
                ]
            },
        },
    )

    # Act & Assert
    with patch.object(scan_lambda.metrics, "add_metric"), patch.object(
        scan_lambda.metrics, "flush_metrics"
    ), patch.dict(
        "os.environ", {"POWERTOOLS_METRICS_NAMESPACE": "test-namespace"}
    ), pytest.raises(
        Exception
    ) as excinfo:
        scan_lambda.scan(
            input_bucket, input_key, download_path, definitions_path, tmp_path
        )

    # Verify exception contains expected data
    exception_data = json.loads(str(excinfo.value))
    assert_that(exception_data["status"]).is_equal_to(
        scan_lambda.ScanStatus.ERROR
    )
    assert_that(exception_data["input_bucket"]).is_equal_to(input_bucket)
    assert_that(exception_data["input_key"]).is_equal_to(input_key)
    assert_that(s3_stubber).has_no_pending_responses()


@patch("lambda.subprocess.run")
def test_scan_subprocess_error(mock_run, s3_stubber):
    # Arrange
    mock_run.side_effect = subprocess.CalledProcessError(
        1, "clamscan", output=b"Error output"
    )
    input_bucket = "test-bucket"
    input_key = "test-file.txt"
    download_path = tempfile.mkdtemp()
    definitions_path = "/tmp/defs"
    tmp_path = "/tmp/tmp-path"

    # Stub the get_object_tagging call for set_status and report_failure
    s3_stubber.add_response(
        "get_object_tagging",
        {"TagSet": []},
        {"Bucket": input_bucket, "Key": input_key},
    )

    # Stub the put_object_tagging call for set_status and report_failure
    s3_stubber.add_response(
        "put_object_tagging",
        {},
        {
            "Bucket": input_bucket,
            "Key": input_key,
            "Tagging": {
                "TagSet": [
                    {
                        "Key": "scan-status",
                        "Value": scan_lambda.ScanStatus.ERROR,
                    }
                ]
            },
        },
    )

    # Act & Assert
    with patch.object(scan_lambda.metrics, "add_metric"), patch.object(
        scan_lambda.metrics, "flush_metrics"
    ), patch.dict(
        "os.environ", {"POWERTOOLS_METRICS_NAMESPACE": "test-namespace"}
    ), pytest.raises(
        Exception
    ) as excinfo:
        scan_lambda.scan(
            input_bucket, input_key, download_path, definitions_path, tmp_path
        )

    # Verify exception contains expected data
    exception_data = json.loads(str(excinfo.value))
    assert_that(exception_data["status"]).is_equal_to(
        scan_lambda.ScanStatus.ERROR
    )
    assert_that(exception_data["input_bucket"]).is_equal_to(input_bucket)
    assert_that(exception_data["input_key"]).is_equal_to(input_key)
    assert_that(s3_stubber).has_no_pending_responses()


@patch("os.path.exists")
@patch("os.remove")
def test_delete_file(mock_remove, mock_exists):
    # Arrange
    mock_exists.return_value = True
    download_path = tempfile.mkdtemp()
    input_key = "test-file.txt"

    # Act
    scan_lambda.delete(download_path, input_key)

    # Assert
    mock_remove.assert_called_once_with(f"{download_path}/{input_key}")


@patch("os.path.exists")
@patch("shutil.rmtree")
def test_delete_directory(mock_rmtree, mock_exists):
    # Arrange
    mock_exists.return_value = True
    download_path = tempfile.mkdtemp()

    # Act
    scan_lambda.delete(download_path)

    # Assert
    mock_rmtree.assert_called_once_with(download_path)


def test_report_failure():
    # Arrange
    with patch.object(
        scan_lambda, "set_status"
    ) as mock_set_status, patch.object(
        scan_lambda, "delete"
    ) as mock_delete, patch.object(
        scan_lambda.logger, "error"
    ) as mock_logger_error:
        input_bucket = "test-bucket"
        input_key = "test-file.txt"
        download_path = tempfile.mkdtemp()
        message = "Test error message"
        version_id = "v1"

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            scan_lambda.report_failure(
                input_bucket, input_key, download_path, message, version_id
            )

        # Verify exception contains expected data
        exception_data = json.loads(str(excinfo.value))
        assert_that(exception_data["status"]).is_equal_to(
            scan_lambda.ScanStatus.ERROR
        )
        assert_that(exception_data["input_bucket"]).is_equal_to(input_bucket)
        assert_that(exception_data["input_key"]).is_equal_to(input_key)
        assert_that(exception_data["message"]).is_equal_to(message)
        assert_that(exception_data["version_id"]).is_equal_to(version_id)

        # Verify mocks were called
        mock_set_status.assert_called_once_with(
            input_bucket, input_key, scan_lambda.ScanStatus.ERROR, version_id
        )
        mock_delete.assert_called_once_with(download_path)
        mock_logger_error.assert_called_once()
