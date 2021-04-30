# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import boto3
import logging
import botocore
import urllib3
import json
import time


logger = logging.getLogger()
logger.setLevel(logging.INFO)
http = urllib3.PoolManager()
SUCCESS = "SUCCESS"
FAILED = "FAILED"

sfn_client = boto3.client("stepfunctions")
lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    """Custom Resource to populate initial Virus definitions"""
    event_type = event["RequestType"]
    if event_type == "Create":
        try:
            fn_name = event["ResourceProperties"]["FnName"]
            result = lambda_client.invoke(FunctionName=fn_name)
            error = result.get("FunctionError")
            if not error:
                reason = "Initial definition download succeeded"
                logger.info(reason)
                return send(event, context, SUCCESS, {}, reason=reason)
            else:
                reason = f"Initial definition download failed: {error}"
                logger.error(reason)
                return send(event, context, FAILED, {}, reason=reason)
        except botocore.exceptions.ClientError as e:
            logger.error(e)
            return send(event, context, FAILED, {}, reason=e)
    else:
        reason = f"Nothing to do on {event_type}"
        logger.info(reason)
        return send(event, context, SUCCESS, {}, reason=reason)


def send(
    event,
    context,
    responseStatus,
    responseData,
    physicalResourceId=None,
    noEcho=False,
    reason=None,
):
    """Send response to CloudFormation"""
    responseUrl = event["ResponseURL"]
    logger.info(responseUrl)
    responseBody = {
        "Status": responseStatus,
        "Reason": reason
        or f"See the details in CloudWatch Log Stream: {context.log_stream_name}",
        "PhysicalResourceId": physicalResourceId or context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "NoEcho": noEcho,
        "Data": responseData,
    }
    json_responseBody = json.dumps(responseBody)
    logger.info("Response body:")
    logger.info(json_responseBody)
    headers = {
        "content-type": "",
        "content-length": str(len(json_responseBody)),
    }
    try:
        response = http.request(
            "PUT", responseUrl, headers=headers, body=json_responseBody
        )
        logger.info(f"Status code: {response.status}")
    except Exception as e:
        logger.info(f"send(..) failed executing http.request(..): {e}")
