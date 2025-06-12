from unittest.mock import patch
import importlib
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
    s3_client = boto3.client('s3')
    with Stubber(s3_client) as stubber:
        # Replace the global s3_client in the lambda module with our stubbed client
        original_client = scan_lambda.s3_client
        scan_lambda.s3_client = s3_client
        yield stubber
        # Restore the original client after the test
        scan_lambda.s3_client = original_client


class DummyContext:
    aws_request_id = "req-1"
    function_name = "test-function"
    memory_limit_in_mb = 512
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"


def test_set_status_versioned(s3_stubber):
    # Arrange
    bucket = "bucket"
    key = "key"
    status = scan_lambda.ScanStatus.CLEAN
    version_id = "v1"
    
    # Stub the get_object_tagging call
    s3_stubber.add_response(
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': bucket, 'Key': key, 'VersionId': version_id}
    )
    
    # Stub the put_object_tagging call
    expected_tags = {'TagSet': [{'Key': 'scan-status', 'Value': status}]}
    s3_stubber.add_response(
        'put_object_tagging',
        {},
        {'Bucket': bucket, 'Key': key, 'Tagging': expected_tags, 'VersionId': version_id}
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
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': bucket, 'Key': key}
    )
    
    # Stub the put_object_tagging call
    expected_tags = {'TagSet': [{'Key': 'scan-status', 'Value': status}]}
    s3_stubber.add_response(
        'put_object_tagging',
        {},
        {'Bucket': bucket, 'Key': key, 'Tagging': expected_tags}
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
        'get_object_tagging',
        {'TagSet': [{'Key': 'scan-status', 'Value': expected_status}]},
        {'Bucket': bucket, 'Key': key, 'VersionId': version_id}
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
        'get_object_tagging',
        {'TagSet': [{'Key': 'scan-status', 'Value': expected_status}]},
        {'Bucket': bucket, 'Key': key}
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
    error_response = {
        'Error': {
            'Code': 'NoSuchKey',
            'Message': 'Not found'
        }
    }
    s3_stubber.add_client_error(
        'get_object_tagging',
        service_error_code='NoSuchKey',
        service_message='Not found',
        http_status_code=404,
        expected_params={'Bucket': bucket, 'Key': key, 'VersionId': version_id}
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
        'get_object_tagging',
        {'TagSet': [{'Key': 'foo', 'Value': expected_value}]},
        {'Bucket': bucket, 'Key': key, 'VersionId': version_id}
    )

    # Act
    value = scan_lambda.get_tag_value(bucket, key, tag_key, version_id=version_id)

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
        'get_object_tagging',
        {'TagSet': [{'Key': 'foo', 'Value': 'bar'}]},
        {'Bucket': bucket, 'Key': key}
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
    
    # First, stub the get_object_tagging call for get_status
    s3_stubber.add_response(
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': 'test-bucket', 'Key': 'test.txt', 'VersionId': 'abc123'}
    )
    
    # Second, stub the get_object_tagging call for set_status
    s3_stubber.add_response(
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': 'test-bucket', 'Key': 'test.txt', 'VersionId': 'abc123'}
    )
    
    # Third, stub the put_object_tagging call for set_status
    s3_stubber.add_response(
        'put_object_tagging',
        {},
        {
            'Bucket': 'test-bucket', 
            'Key': 'test.txt', 
            'Tagging': {'TagSet': [{'Key': 'scan-status', 'Value': scan_lambda.ScanStatus.IN_PROGRESS}]},
            'VersionId': 'abc123'
        }
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
    
    # First, stub the get_object_tagging call for get_status
    s3_stubber.add_response(
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': 'test-bucket', 'Key': 'test.txt'}
    )
    
    # Second, stub the get_object_tagging call for set_status
    s3_stubber.add_response(
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': 'test-bucket', 'Key': 'test.txt'}
    )
    
    # Third, stub the put_object_tagging call for set_status
    s3_stubber.add_response(
        'put_object_tagging',
        {},
        {
            'Bucket': 'test-bucket', 
            'Key': 'test.txt', 
            'Tagging': {'TagSet': [{'Key': 'scan-status', 'Value': scan_lambda.ScanStatus.IN_PROGRESS}]}
        }
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
    s3_stubber,
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
    
    # First, stub the get_object_tagging call for get_status
    s3_stubber.add_response(
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': 'test-bucket', 'Key': 'test.txt', 'VersionId': 'abc123'}
    )
    
    # Second, stub the get_object_tagging call for set_status
    s3_stubber.add_response(
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': 'test-bucket', 'Key': 'test.txt', 'VersionId': 'abc123'}
    )
    
    # Third, stub the put_object_tagging call for set_status
    s3_stubber.add_response(
        'put_object_tagging',
        {},
        {
            'Bucket': 'test-bucket', 
            'Key': 'test.txt', 
            'Tagging': {'TagSet': [{'Key': 'scan-status', 'Value': scan_lambda.ScanStatus.IN_PROGRESS}]},
            'VersionId': 'abc123'
        }
    )

    # Act
    with patch.dict("os.environ", env_vars):
        result = original_handler(s3_event_versioned, ctx)

    # Assert
    assert_that(result).has_status(expected_status)
    assert_that(result).has_version_id(expected_version_id)
    assert_that(s3_stubber).has_no_pending_responses()


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
    s3_stubber,
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
    
    # First, stub the get_object_tagging call for get_status
    s3_stubber.add_response(
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': 'test-bucket', 'Key': 'test.txt'}
    )
    
    # Second, stub the get_object_tagging call for set_status
    s3_stubber.add_response(
        'get_object_tagging',
        {'TagSet': []},
        {'Bucket': 'test-bucket', 'Key': 'test.txt'}
    )
    
    # Third, stub the put_object_tagging call for set_status
    s3_stubber.add_response(
        'put_object_tagging',
        {},
        {
            'Bucket': 'test-bucket', 
            'Key': 'test.txt', 
            'Tagging': {'TagSet': [{'Key': 'scan-status', 'Value': scan_lambda.ScanStatus.IN_PROGRESS}]}
        }
    )

    # Act
    with patch.dict("os.environ", env_vars):
        result = original_handler(s3_event_unversioned, ctx)

    # Assert
    assert_that(result).has_status(expected_status)
    assert_that(s3_stubber).has_no_pending_responses()
