# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.8
LABEL name=lambda/python/clamav
LABEL version=1.0

ARG CACHE_DATE=1
RUN yum update -y \
    && yum install -y amazon-linux-extras \
    && PYTHON=python2 amazon-linux-extras install epel \
    && yum -y install clamav clamd \
    && yum clean all \
    && pip3 install --no-cache-dir cffi awslambdaric boto3 requests aws-lambda-powertools \
    && ln -s /etc/freshclam.conf /tmp/freshclam.conf

COPY clamd.conf /etc/clamd.conf
COPY lambda.py /var/task/lambda.py
ENTRYPOINT [ "/var/lang/bin/python3", "-m", "awslambdaric" ]
CMD [ "lambda.lambda_handler" ]