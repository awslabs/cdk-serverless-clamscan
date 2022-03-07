// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { ABSENT, anything, arrayWith, stringLike } from '@aws-cdk/assert';
import { EventBus } from '@aws-cdk/aws-events';
import { SqsDestination, EventBridgeDestination } from '@aws-cdk/aws-lambda-destinations';
import { Bucket } from '@aws-cdk/aws-s3';
import { Queue } from '@aws-cdk/aws-sqs';
import { CfnOutput, Fn, Stack } from '@aws-cdk/core';
import { ServerlessClamscan } from '../src';
import '@aws-cdk/assert/jest';


test('expect default EventBridge Lambda destination and Event Rules for onSuccess and SQS Destination for onDelete', () => {
  const stack = new Stack();
  new ServerlessClamscan(stack, 'default', {});
  expect(stack).toHaveResourceLike('AWS::Lambda::EventInvokeConfig', {
    DestinationConfig: {
      OnSuccess: {
        Destination: { 'Fn::GetAtt': arrayWith(stringLike('*ScanResultBus*')) },
      },
    },
  });
  const statuses = ['CLEAN', 'INFECTED'];
  statuses.forEach(status => {
    expect(stack).toHaveResourceLike('AWS::Events::Rule', {
      EventBusName: {
        Ref: stringLike('*ScanResultBus*'),
      },
      EventPattern: {
        detail: {
          responsePayload: {
            source: ['serverless-clamscan'],
            status: [status],
          },
        },
      },
    });
  });
  expect(stack).toHaveResourceLike('AWS::Lambda::EventInvokeConfig', {
    DestinationConfig: {
      OnFailure: {
        Destination: { 'Fn::GetAtt': arrayWith(stringLike('*ScanErrorQueue*')) },
      },
    },
  });
});

test('expect onSuccess to have a SQS queue destination', () => {
  const stack = new Stack();
  const queue = new Queue(stack, 'rQueue');
  new ServerlessClamscan(stack, 'default', { onResult: new SqsDestination(queue) });
  expect(stack).toHaveResourceLike('AWS::Lambda::EventInvokeConfig', {
    DestinationConfig: {
      OnSuccess: {
        Destination: {
          'Fn::GetAtt': [
            stringLike('rQueue*'),
            'Arn',
          ],
        },
      },
    },
  });
  expect(stack).toHaveResourceLike('AWS::Lambda::EventInvokeConfig', {
    DestinationConfig: {
      OnFailure: {
        Destination: { 'Fn::GetAtt': arrayWith(stringLike('*ScanErrorQueue*')) },
      },
    },
  });
  expect(stack).toCountResources('AWS::Lambda::EventInvokeConfig', 1);
});

test('expect onFailure to have an EventBridge destination', () => {
  const stack = new Stack();
  const bus = new EventBus(stack, 'rScanFailBus');
  new ServerlessClamscan(stack, 'default', { onError: new EventBridgeDestination(bus) });
  expect(stack).toHaveResourceLike('AWS::Lambda::EventInvokeConfig', {
    DestinationConfig: {
      OnSuccess: {
        Destination: { 'Fn::GetAtt': arrayWith(stringLike('*ScanResultBus*')) },
      },
    },
  });
  expect(stack).toHaveResourceLike('AWS::Lambda::EventInvokeConfig', {
    DestinationConfig: {
      OnFailure: {
        Destination: { 'Fn::GetAtt': arrayWith(stringLike('*ScanFailBus*')) },
      },
    },
  });
  expect(stack).toCountResources('AWS::Lambda::EventInvokeConfig', 1);
});

test('expect default resources to use encryption when available', () => {
  const stack = new Stack();
  new ServerlessClamscan(stack, 'default', {});
  expect(stack).not.toHaveResourceLike('AWS::S3::Bucket', {
    BucketEncryption: ABSENT,
  });
  expect(stack).not.toHaveResourceLike('AWS::EFS::FileSystem', {
    Encrypted: false,
  });
  expect(stack).not.toHaveResourceLike('AWS::SQS::Queue', {
    KmsMasterKeyId: ABSENT,
  });
});

test('expect ScanVpc to have FlowLogs enabled', () => {
  const stack = new Stack();
  new ServerlessClamscan(stack, 'default', {});
  expect(stack).toHaveResourceLike('AWS::EC2::FlowLog', {
    ResourceId: { Ref: stringLike('*ScanVPC*') },
  });
});

test('expect VirusDefsBucket to use created access logs bucket by default', () => {
  const stack = new Stack();
  new ServerlessClamscan(stack, 'default', {});
  expect(stack).toHaveResourceLike('AWS::S3::Bucket', {
    LoggingConfiguration: {
      DestinationBucketName: {
        Ref: stringLike('*VirusDefsAccessLogsBucket*'),
      },
      LogFilePrefix: ABSENT,
    },
  });
});

test('expect VirusDefsBucket to use provided logs bucket', () => {
  const stack = new Stack();
  const logs_bucket = new Bucket(stack, 'rLogsBucket');
  new ServerlessClamscan(stack, 'default', {
    defsBucketAccessLogsConfig: { logsBucket: logs_bucket },
  });
  new CfnOutput(stack, 'rLogsBucketArnExport', {
    value: logs_bucket.bucketArn,
    exportName: 'rLogsBucketArn',
  });

  expect(stack).toHaveResourceLike('AWS::S3::Bucket', {
    LoggingConfiguration: {
      DestinationBucketName: {
        Ref: stringLike('*rLogsBucket*'),
      },
      LogFilePrefix: ABSENT,
    },
  });
  const stack2 = new Stack();
  const logs_bucket2 = new Bucket(stack2, 'rLogsBucket');
  new ServerlessClamscan(stack2, 'default', {
    defsBucketAccessLogsConfig: { logsBucket: logs_bucket2, logsPrefix: 'test' },
  });
  expect(stack2).toHaveResourceLike('AWS::S3::Bucket', {
    LoggingConfiguration: {
      DestinationBucketName: {
        Ref: stringLike('*rLogsBucket*'),
      },
      LogFilePrefix: 'test',
    },
  });

  const stack3 = new Stack();
  const imported_logs_bucket = Bucket.fromBucketArn(stack3, 'rImportedLogsBucket', Fn.importValue('rLogsBucketArn'));
  new ServerlessClamscan(stack3, 'default', {
    defsBucketAccessLogsConfig: { logsBucket: imported_logs_bucket },
  });
  expect(stack3).toHaveResourceLike('AWS::S3::Bucket', {
    LoggingConfiguration: {
      DestinationBucketName:
      {
        'Fn::Select': [
          0,
          {
            'Fn::Split': [
              '/',
              {
                'Fn::Select': [
                  5,
                  {
                    'Fn::Split': [
                      ':',
                      {
                        'Fn::ImportValue': stringLike('*rLogsBucket*'),
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
      LogFilePrefix: ABSENT,
    },
  });
});

test('expect VirusDefsBucket to not have access logging enabled', () => {
  const stack = new Stack();
  new ServerlessClamscan(stack, 'default', {
    defsBucketAccessLogsConfig: { logsBucket: false, logsPrefix: 'test' },
  });
  expect(stack).toHaveResourceLike('AWS::S3::Bucket', {
    LoggingConfiguration: ABSENT,
  });
});

test('expect reserved concurrency prop to set scan Lambda reserved concurrency', () => {
  const stack = new Stack();
  new ServerlessClamscan(stack, 'default', {
    reservedConcurrency: 100,
  });
  expect(stack).toHaveResourceLike('AWS::Lambda::Function', {
    ReservedConcurrentExecutions: 100,
  });
});

test('expect no reserved concurrency settings by default', () => {
  const stack = new Stack();
  new ServerlessClamscan(stack, 'default', {});
  expect(stack).not.toHaveResourceLike('AWS::Lambda::Function', {
    ReservedConcurrentExecutions: anything(),
  });
});

test('check bucket triggers and policies for source buckets ', () => {
  const stack = new Stack();
  const bucket_1 = new Bucket(stack, 'rBucket1');
  const bucket_2 = new Bucket(stack, 'rBucket2');
  const bucketList = [bucket_1, bucket_2];
  const sc = new ServerlessClamscan(stack, 'default', { buckets: bucketList });
  expect(stack).toCountResources('AWS::S3::BucketPolicy', 4);

  const bucket_3 = new Bucket(stack, 'rBucket3');
  sc.addSourceBucket(bucket_3);
  expect(stack).toCountResources('AWS::S3::BucketPolicy', 5);
  bucketList.push(bucket_3);
  bucketList.forEach(bucket => {
    const approxId = bucket.node.id + '*';
    expect(stack).toHaveResource('AWS::Lambda::Permission', {
      Action: 'lambda:InvokeFunction',
      FunctionName: {
        'Fn::GetAtt': [
          stringLike('*ServerlessClamscan*'),
          'Arn',
        ],
      },
      Principal: 's3.amazonaws.com',
      SourceAccount: {
        Ref: 'AWS::AccountId',
      },
      SourceArn: {
        'Fn::GetAtt': [
          stringLike(approxId),
          'Arn',
        ],
      },
    });
    expect(stack).toHaveResource('AWS::S3::BucketPolicy', {
      Bucket: {
        Ref: stringLike(approxId),
      },
      PolicyDocument: {
        Statement: [
          {
            Action: 's3:GetObject',
            Condition: {
              StringEquals: {
                's3:ExistingObjectTag/scan-status': [
                  'IN PROGRESS',
                  'INFECTED',
                  'ERROR',
                ],
              },
            },
            Effect: 'Deny',
            NotPrincipal: {
              AWS: [{
                'Fn::GetAtt': [
                  stringLike('*ServerlessClamscan*'),
                  'Arn',
                ],
              },
              {
                'Fn::Join': ['', arrayWith(stringLike('*sts*'), stringLike('*assumed-role*'), { Ref: stringLike('*ServerlessClamscan*') })],
              }],
            },
            Resource: {
              'Fn::Join': [
                '',
                [
                  {
                    'Fn::GetAtt': [
                      stringLike(approxId),
                      'Arn',
                    ],
                  },
                  '/*',
                ],
              ],
            },
          },
        ],
        Version: '2012-10-17',
      },
    });
  });
});

test('check Virus Definition buckets policy security and S3 Gateway endpoint policy', () => {
  const stack = new Stack();

  new ServerlessClamscan(stack, 'default', {});
  expect(stack).toCountResources('AWS::S3::BucketPolicy', 2);
  const virusDefs = '*VirusDefs*';
  try {
    expect(stack).toHaveResource('AWS::S3::BucketPolicy', {
      Bucket: {
        Ref: stringLike(virusDefs),
      },
      PolicyDocument: {
        Statement: arrayWith(
          {
            Action: 's3:*',
            Condition: {
              Bool: {
                'aws:SecureTransport': false,
              },
            },
            Effect: 'Deny',
            Principal: { AWS: '*' },
            Resource: [{
              'Fn::Join': [
                '',
                [
                  {
                    'Fn::GetAtt': [
                      stringLike(virusDefs),
                      'Arn',
                    ],
                  },
                  '/*',
                ],
              ],
            },
            {
              'Fn::GetAtt': [
                stringLike(virusDefs),
                'Arn',
              ],
            }],
          },
          {
            Action: [
              's3:PutBucketPolicy',
              's3:DeleteBucketPolicy',
            ],
            Effect: 'Deny',
            NotPrincipal: {
              AWS: {
                'Fn::Join': [
                  '',
                  [
                    'arn:',
                    {
                      Ref: 'AWS::Partition',
                    },
                    ':iam::',
                    {
                      Ref: 'AWS::AccountId',
                    },
                    ':root',
                  ],
                ],
              },
            },
            Resource: {
              'Fn::GetAtt': [
                stringLike(virusDefs),
                'Arn',
              ],
            },
          },
          {
            Action: [
              's3:GetObject',
              's3:ListBucket',
            ],
            Condition: {
              StringEquals: {
                'aws:SourceVpce': {
                  Ref: stringLike('*Scan*S3Endpoint*'),
                },
              },
            },
            Effect: 'Allow',
            Principal: { AWS: '*' },
            Resource: [{
              'Fn::Join': [
                '',
                [
                  {
                    'Fn::GetAtt': [
                      stringLike(virusDefs),
                      'Arn',
                    ],
                  },
                  '/*',
                ],
              ],
            },
            {
              'Fn::GetAtt': [
                stringLike(virusDefs),
                'Arn',
              ],
            }],
          },
          {
            Action: 's3:PutObject*',
            Effect: 'Deny',
            NotPrincipal: {
              AWS: [
                {
                  'Fn::GetAtt': [
                    stringLike('*DownloadDefs*'),
                    'Arn',
                  ],
                },
                {
                  'Fn::Join': [
                    '',
                    [
                      'arn:',
                      {
                        Ref: 'AWS::Partition',
                      },
                      ':sts::',
                      {
                        Ref: 'AWS::AccountId',
                      },
                      ':assumed-role/',
                      {
                        Ref: stringLike('*DownloadDefs*'),
                      },
                      '/',
                      {
                        Ref: stringLike('*DownloadDefs*'),
                      },
                    ],
                  ],
                },
              ],
            },
            Resource: {
              'Fn::Join': [
                '',
                [
                  {
                    'Fn::GetAtt': [
                      stringLike(virusDefs),
                      'Arn',
                    ],
                  },
                  '/*',
                ],
              ],
            },
          },
        ),
        Version: '2012-10-17',
      },
    });

  } catch (error) {
    expect(stack).toHaveResource('AWS::S3::BucketPolicy', {
      Bucket: {
        Ref: stringLike(virusDefs),
      },
      PolicyDocument: {
        Statement: arrayWith(
          {
            Action: 's3:*',
            Condition: {
              Bool: {
                'aws:SecureTransport': false,
              },
            },
            Effect: 'Deny',
            Principal: '*',
            Resource: [{
              'Fn::Join': [
                '',
                [
                  {
                    'Fn::GetAtt': [
                      stringLike(virusDefs),
                      'Arn',
                    ],
                  },
                  '/*',
                ],
              ],
            },
            {
              'Fn::GetAtt': [
                stringLike(virusDefs),
                'Arn',
              ],
            }],
          },
          {
            Action: [
              's3:PutBucketPolicy',
              's3:DeleteBucketPolicy',
            ],
            Effect: 'Deny',
            NotPrincipal: {
              AWS: {
                'Fn::Join': [
                  '',
                  [
                    'arn:',
                    {
                      Ref: 'AWS::Partition',
                    },
                    ':iam::',
                    {
                      Ref: 'AWS::AccountId',
                    },
                    ':root',
                  ],
                ],
              },
            },
            Resource: {
              'Fn::GetAtt': [
                stringLike(virusDefs),
                'Arn',
              ],
            },
          },
          {
            Action: [
              's3:GetObject',
              's3:ListBucket',
            ],
            Condition: {
              StringEquals: {
                'aws:SourceVpce': {
                  Ref: stringLike('*Scan*S3Endpoint*'),
                },
              },
            },
            Effect: 'Allow',
            Principal: '*',
            Resource: [{
              'Fn::Join': [
                '',
                [
                  {
                    'Fn::GetAtt': [
                      stringLike(virusDefs),
                      'Arn',
                    ],
                  },
                  '/*',
                ],
              ],
            },
            {
              'Fn::GetAtt': [
                stringLike(virusDefs),
                'Arn',
              ],
            }],
          },
          {
            Action: 's3:PutObject*',
            Effect: 'Deny',
            NotPrincipal: {
              AWS: [
                {
                  'Fn::GetAtt': [
                    stringLike('*DownloadDefs*'),
                    'Arn',
                  ],
                },
                {
                  'Fn::Join': [
                    '',
                    [
                      'arn:',
                      {
                        Ref: 'AWS::Partition',
                      },
                      ':sts::',
                      {
                        Ref: 'AWS::AccountId',
                      },
                      ':assumed-role/',
                      {
                        Ref: stringLike('*DownloadDefs*'),
                      },
                      '/',
                      {
                        Ref: stringLike('*DownloadDefs*'),
                      },
                    ],
                  ],
                },
              ],
            },
            Resource: {
              'Fn::Join': [
                '',
                [
                  {
                    'Fn::GetAtt': [
                      stringLike(virusDefs),
                      'Arn',
                    ],
                  },
                  '/*',
                ],
              ],
            },
          },
        ),
        Version: '2012-10-17',
      },
    });
  }
  try {
    expect(stack).toHaveResource('AWS::EC2::VPCEndpoint', {
      PolicyDocument: {
        Statement: [
          {
            Action: [
              's3:GetObject',
              's3:ListBucket',
            ],
            Effect: 'Allow',
            Principal: { AWS: '*' },
            Resource: [
              {
                'Fn::Join': [
                  '',
                  [
                    {
                      'Fn::GetAtt': [
                        stringLike(virusDefs),
                        'Arn',
                      ],
                    },
                    '/*',
                  ],
                ],
              },
              {
                'Fn::GetAtt': [
                  stringLike(virusDefs),
                  'Arn',
                ],
              },
            ],
          },
        ],
        Version: '2012-10-17',
      },
    });
  } catch (error) {
    expect(stack).toHaveResource('AWS::EC2::VPCEndpoint', {
      PolicyDocument: {
        Statement: [
          {
            Action: [
              's3:GetObject',
              's3:ListBucket',
            ],
            Effect: 'Allow',
            Principal: '*',
            Resource: [
              {
                'Fn::Join': [
                  '',
                  [
                    {
                      'Fn::GetAtt': [
                        stringLike(virusDefs),
                        'Arn',
                      ],
                    },
                    '/*',
                  ],
                ],
              },
              {
                'Fn::GetAtt': [
                  stringLike(virusDefs),
                  'Arn',
                ],
              },
            ],
          },
        ],
        Version: '2012-10-17',
      },
    });
  }

});

test('Check definition downloading event and custom resource permissions ', () => {
  const stack = new Stack();
  new ServerlessClamscan(stack, 'default', {});
  expect(stack).toHaveResource('AWS::CloudFormation::CustomResource', {
    FnName: {
      Ref: stringLike('*DownloadDefs*'),
    },
  });
  expect(stack).toHaveResourceLike('AWS::IAM::Policy', {
    PolicyDocument: {
      Statement: [
        {
          Action: 'lambda:InvokeFunction',
          Effect: 'Allow',
          Resource: {
            'Fn::GetAtt': [
              stringLike('*DownloadDefs*'),
              'Arn',
            ],
          },
        },
      ],
    },
    Roles: [{ Ref: stringLike('*InitDefsServiceRole*') }],
  });

});

test('Check EFS existence and Lambda Configuration ', () => {
  const stack = new Stack();
  new ServerlessClamscan(stack, 'default', {});
  expect(stack).toCountResources('AWS::EFS::FileSystem', 1);
  expect(stack).toHaveResourceLike('AWS::Lambda::Function', {
    VpcConfig: {
      SecurityGroupIds: arrayWith({ 'Fn::GetAtt': arrayWith(stringLike('*ServerlessClamscan*')) }),
    },
    FileSystemConfigs: [{ Arn: { 'Fn::Join': ['', arrayWith(':elasticfilesystem:')] } }],
  });
});


