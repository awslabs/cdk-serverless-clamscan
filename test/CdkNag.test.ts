// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { SynthUtils } from '@aws-cdk/assert';
import { Aspects, Stack } from 'aws-cdk-lib';
import { AwsSolutionsChecks, NagSuppressions } from 'cdk-nag';
import { ServerlessClamscan } from '../src';

test('expect default configuration to pass cdk-nag AwsSolutions checks', () => {
  const stack = new Stack();
  Aspects.of(stack).add(new AwsSolutionsChecks());
  new ServerlessClamscan(stack, 'default', {});

  NagSuppressions.addResourceSuppressionsByPath(stack, '/Default/default/ScanErrorDeadLetterQueue/Resource', [
    { id: 'AwsSolutions-SQS3', reason: 'This queue is a DLQ.' },
  ]);

  NagSuppressions.addResourceSuppressionsByPath(stack, '/Default/default/ServerlessClamscan/ServiceRole/Resource', [
    { id: 'AwsSolutions-IAM4', reason: 'The AWSLambdaBasicExecutionRole does not provide permissions beyond uploading logs to CloudWatch. The AWSLambdaVPCAccessExecutionRole is required for functions with VPC access to manage elastic network interfaces.' },
  ],
  true,
  );

  NagSuppressions.addResourceSuppressionsByPath(stack, '/Default/default/ServerlessClamscan/ServiceRole/DefaultPolicy/Resource', [
    { id: 'AwsSolutions-IAM5', reason: 'The EFS mount point permissions are controlled through a condition which limit the scope of the * resources.' },
  ]);

  NagSuppressions.addResourceSuppressionsByPath(stack, '/Default/default/DownloadDefs/ServiceRole/Resource', [
    { id: 'AwsSolutions-IAM4', reason: 'The AWSLambdaBasicExecutionRole does not provide permissions beyond uploading logs to CloudWatch.' },
    { id: 'AwsSolutions-IAM5', reason: 'The function is allowed to perform operations on all prefixes in the specified bucket.' },
  ],
  true,
  );

  NagSuppressions.addResourceSuppressionsByPath(stack, '/Default/default/InitDefs/ServiceRole/Resource', [
    { id: 'AwsSolutions-IAM4', reason: 'The AWSLambdaBasicExecutionRole does not provide permissions beyond uploading logs to CloudWatch.' },
    { id: 'AwsSolutions-IAM5', reason: 'The function is allowed to perform operations on all prefixes in the specified bucket.' },
  ],
  true,
  );

  const messages = SynthUtils.synthesize(stack).messages;
  expect(messages).not.toContainEqual(
    expect.objectContaining({
      entry: expect.objectContaining({
        data: expect.stringContaining(
          'AwsSolutions-',
        ),
      }),
    }),
  );
});

