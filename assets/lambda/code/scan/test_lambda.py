from unittest.mock import patch
import importlib
import pytest
# lambda is a reserved keyword in Python, so this import must be done dynamically
scan_lambda = importlib.import_module("lambda")

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


class DummyContext:
    aws_request_id = "req-1"
    function_name = "test-function"
    memory_limit_in_mb = 512
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"


@patch("lambda.s3_client")
def test_set_status_versioned(mock_s3):
    # Arrange
    mock_s3.get_object_tagging.return_value = {"TagSet": []}
    bucket = "bucket"
    key = "key"
    status = scan_lambda.ScanStatus.CLEAN
    version_id = "v1"

    # Act
    scan_lambda.set_status(bucket, key, status, version_id=version_id)

    # Assert
    args = mock_s3.put_object_tagging.call_args[1]
    assert args["VersionId"] == version_id
    assert any(
        tag["Key"] == "scan-status" and tag["Value"] == status
        for tag in args["Tagging"]["TagSet"]
    )


@patch("lambda.s3_client")
def test_set_status_unversioned(mock_s3):
    # Arrange
    mock_s3.get_object_tagging.return_value = {"TagSet": []}
    bucket = "bucket"
    key = "key"
    status = scan_lambda.ScanStatus.CLEAN

    # Act
    scan_lambda.set_status(bucket, key, status)

    # Assert
    args = mock_s3.put_object_tagging.call_args[1]
    assert "VersionId" not in args
    assert any(
        tag["Key"] == "scan-status" and tag["Value"] == status
        for tag in args["Tagging"]["TagSet"]
    )


@patch("lambda.s3_client")
def test_get_status_versioned_found(mock_s3):
    # Arrange
    expected_status = scan_lambda.ScanStatus.CLEAN
    mock_s3.get_object_tagging.return_value = {
        "TagSet": [{"Key": "scan-status", "Value": expected_status}]
    }
    bucket = "bucket"
    key = "key"
    version_id = "v1"

    # Act
    status = scan_lambda.get_status(bucket, key, version_id=version_id)

    # Assert
    assert status == expected_status
    mock_s3.get_object_tagging.assert_called_once_with(
        Bucket=bucket, Key=key, VersionId=version_id
    )


@patch("lambda.s3_client")
def test_get_status_unversioned_found(mock_s3):
    # Arrange
    expected_status = scan_lambda.ScanStatus.CLEAN
    mock_s3.get_object_tagging.return_value = {
        "TagSet": [{"Key": "scan-status", "Value": expected_status}]
    }
    bucket = "bucket"
    key = "key"

    # Act
    status = scan_lambda.get_status(bucket, key)

    # Assert
    assert status == expected_status
    mock_s3.get_object_tagging.assert_called_once_with(Bucket=bucket, Key=key)


@patch("lambda.s3_client")
def test_get_status_deleted(mock_s3):
    # Arrange
    error = scan_lambda.botocore.exceptions.ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObjectTagging"
    )
    mock_s3.get_object_tagging.side_effect = error
    bucket = "bucket"
    key = "key"
    version_id = "v1"

    # Act
    status = scan_lambda.get_status(bucket, key, version_id=version_id)

    # Assert
    assert status == scan_lambda.ScanStatus.DELETED


@patch("lambda.s3_client")
def test_get_tag_value_versioned(mock_s3):
    # Arrange
    expected_value = "bar"
    mock_s3.get_object_tagging.return_value = {
        "TagSet": [{"Key": "foo", "Value": expected_value}]
    }
    bucket = "bucket"
    key = "key"
    tag_key = "foo"
    version_id = "v1"

    # Act
    value = scan_lambda.get_tag_value(bucket, key, tag_key, version_id=version_id)

    # Assert
    assert value == expected_value
    mock_s3.get_object_tagging.assert_called_once_with(
        Bucket=bucket, Key=key, VersionId=version_id
    )


@patch("lambda.s3_client")
def test_get_tag_value_not_found(mock_s3):
    # Arrange
    mock_s3.get_object_tagging.return_value = {
        "TagSet": [{"Key": "foo", "Value": "bar"}]
    }
    bucket = "bucket"
    key = "key"
    tag_key = "baz"  # Different from what's in the TagSet

    # Act
    value = scan_lambda.get_tag_value(bucket, key, tag_key)

    # Assert
    assert value is None


@patch("lambda.set_status")
@patch("lambda.get_status", return_value=None)
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
    mock_get_status,
    mock_set_status,
    s3_event_versioned,
):
    # Arrange
    ctx = DummyContext()
    expected_status = scan_lambda.ScanStatus.CLEAN
    env_vars = {
        "EFS_DEF_PATH": "defs",
        "EFS_MOUNT_PATH": "/tmp",
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

    # Act
    with patch.dict("os.environ", env_vars):
        result = original_handler(s3_event_versioned, ctx)

    # Assert
    assert result["status"] == expected_status
    assert result["version_id"] == "abc123"
    mock_get_status.assert_called_once_with("test-bucket", "test.txt", "abc123")
    mock_set_status.assert_called_once_with("test-bucket", "test.txt", scan_lambda.ScanStatus.IN_PROGRESS, "abc123")
    mock_create.assert_called()
    mock_download.assert_called()
    mock_expand.assert_called()
    mock_freshclam.assert_called()
    mock_scan.assert_called()
    mock_delete.assert_called()


@patch("lambda.set_status")
@patch("lambda.get_status", return_value=None)
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
    mock_get_status,
    mock_set_status,
    s3_event_unversioned,
):
    # Arrange
    ctx = DummyContext()
    expected_status = scan_lambda.ScanStatus.CLEAN
    env_vars = {
        "EFS_DEF_PATH": "defs",
        "EFS_MOUNT_PATH": "/tmp",
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

    # Act
    with patch.dict("os.environ", env_vars):
        result = original_handler(s3_event_unversioned, ctx)

    # Assert
    assert result["status"] == expected_status
    assert "version_id" not in result
    mock_get_status.assert_called_once_with("test-bucket", "test.txt", None)
    mock_set_status.assert_called_once_with("test-bucket", "test.txt", scan_lambda.ScanStatus.IN_PROGRESS, None)
    mock_create.assert_called()
    mock_download.assert_called()
    mock_expand.assert_called()
    mock_freshclam.assert_called()
    mock_scan.assert_called()
    mock_delete.assert_called()


@patch("lambda.set_status")
@patch("lambda.get_status", return_value=None)
@patch("lambda.create_dir")
@patch("lambda.download_object")
@patch("lambda.expand_if_large_archive")
@patch("lambda.freshclam_update")
@patch("lambda.scan", return_value={"status": scan_lambda.ScanStatus.CLEAN})
@patch("lambda.delete")
@patch("lambda.metrics")
def test_lambda_handler_versioned_no_metrics(
    mock_metrics,
    mock_delete,
    mock_scan,
    mock_freshclam,
    mock_expand,
    mock_download,
    mock_create,
    mock_get_status,
    mock_set_status,
    s3_event_versioned,
):
    # Arrange
    ctx = DummyContext()
    expected_version_id = "abc123"
    expected_status = scan_lambda.ScanStatus.CLEAN
    env_vars = {"EFS_MOUNT_PATH": "/tmp", "EFS_DEF_PATH": "defs"}

    # Disable metrics collection completely in tests
    # Create a mock that does nothing when these methods are called
    mock_metrics.log_metrics = lambda *args, **kwargs: lambda fn: fn
    mock_metrics.namespace = "test-namespace"
    mock_metrics.add_metric.return_value = None
    mock_metrics.flush_metrics.return_value = None
    mock_metrics.add_dimension.return_value = None

    # Act
    with patch.dict("os.environ", env_vars):
        result = original_handler(s3_event_versioned, ctx)

    # Assert
    assert result["status"] == expected_status
    assert result["version_id"] == expected_version_id


@patch("lambda.set_status")
@patch("lambda.get_status", return_value=None)
@patch("lambda.create_dir")
@patch("lambda.download_object")
@patch("lambda.expand_if_large_archive")
@patch("lambda.freshclam_update")
@patch("lambda.scan", return_value={"status": scan_lambda.ScanStatus.CLEAN})
@patch("lambda.delete")
@patch("lambda.metrics")
def test_lambda_handler_unversioned_no_metrics(
    mock_metrics,
    mock_delete,
    mock_scan,
    mock_freshclam,
    mock_expand,
    mock_download,
    mock_create,
    mock_get_status,
    mock_set_status,
    s3_event_unversioned,
):
    # Arrange
    ctx = DummyContext()
    expected_status = scan_lambda.ScanStatus.CLEAN
    env_vars = {
        "EFS_DEF_PATH": "defs",
        "EFS_MOUNT_PATH": "/tmp",
        "POWERTOOLS_METRICS_NAMESPACE": "test-namespace",
        "POWERTOOLS_SERVICE_NAME": "test-service",
    }

    # Disable metrics collection completely in tests
    mock_metrics.log_metrics = lambda *args, **kwargs: lambda fn: fn
    mock_metrics.namespace = "test-namespace"
    mock_metrics.add_metric.return_value = None
    mock_metrics.flush_metrics.return_value = None
    mock_metrics.add_dimension.return_value = None

    # Act
    with patch.dict("os.environ", env_vars):
        result = original_handler(s3_event_unversioned, ctx)

    # Assert
    assert result["status"] == expected_status
    mock_get_status.assert_called_once_with("test-bucket", "test.txt", None)
    mock_set_status.assert_called_once_with("test-bucket", "test.txt", scan_lambda.ScanStatus.IN_PROGRESS, None)
    mock_create.assert_called()
    mock_download.assert_called()
    mock_expand.assert_called()
    mock_freshclam.assert_called()
    mock_scan.assert_called()
    mock_delete.assert_called()
