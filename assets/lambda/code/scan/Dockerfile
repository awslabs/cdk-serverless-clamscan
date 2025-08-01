# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.12
LABEL name=lambda/python/clamav
LABEL version=1.0

ARG CACHE_DATE=1
COPY requirements.in /var/task/requirements.in
RUN dnf update -y \
    && dnf -y install clamav1.4 clamd1.4 p7zip \
    && dnf clean all \
    && pip3 install --no-cache-dir -r /var/task/requirements.in awslambdaric \
    && ln -s /etc/freshclam.conf /tmp/freshclam.conf

# Copy requirements file and install dependencies

COPY clamd.conf /etc/clamd.conf
COPY lambda.py /var/task/lambda.py
ENTRYPOINT [ "/var/lang/bin/python3", "-m", "awslambdaric" ]
CMD [ "lambda.lambda_handler" ]