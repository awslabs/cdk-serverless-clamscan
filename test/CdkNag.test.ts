// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { SynthUtils } from '@aws-cdk/assert';
import { Aspects, Stack } from '@aws-cdk/core';
import { AwsSolutionsChecks } from 'cdk-nag';
import { ServerlessClamscan } from '../src';

test('expect default configuration to pass cdk-nag AwsSolutions checks', () => {
  const stack = new Stack();
  Aspects.of(stack).add(new AwsSolutionsChecks());
  new ServerlessClamscan(stack, 'default', {});
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

