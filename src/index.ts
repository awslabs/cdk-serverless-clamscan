// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as path from 'path';
import {
  Vpc,
  SubnetType,
  GatewayVpcEndpoint,
  GatewayVpcEndpointAwsService,
  Port,
  SecurityGroup,
} from '@aws-cdk/aws-ec2';
import { FileSystem, LifecyclePolicy, PerformanceMode } from '@aws-cdk/aws-efs';
import { EventBus, Rule, Schedule } from '@aws-cdk/aws-events';
import { LambdaFunction } from '@aws-cdk/aws-events-targets';
import {
  Effect,
  PolicyStatement,
  ArnPrincipal,
  AnyPrincipal,
  AccountRootPrincipal,
  CfnRole,
} from '@aws-cdk/aws-iam';
import {
  DockerImageCode,
  DockerImageFunction,
  Function,
  IDestination,
  FileSystem as LambdaFileSystem,
  Runtime,
  Code,
} from '@aws-cdk/aws-lambda';
import {
  EventBridgeDestination,
  SqsDestination,
} from '@aws-cdk/aws-lambda-destinations';
import { S3EventSource } from '@aws-cdk/aws-lambda-event-sources';
import { Bucket, BucketEncryption, EventType } from '@aws-cdk/aws-s3';
import { CfnQueue, Queue, QueueEncryption } from '@aws-cdk/aws-sqs';
import {
  Construct,
  Duration,
  CustomResource,
  RemovalPolicy,
  Stack,
  CfnResource,
} from '@aws-cdk/core';

/**
 * Interface for ServerlessClamscan Virus Definitions S3 Bucket Logging.
 */
export interface ServerlessClamscanLoggingProps {
  /**
   * Destination bucket for the server access logs (Default: Creates a new S3 Bucket for access logs ).
   */
  readonly logsBucket?: boolean | Bucket;
  /**
   * Optional log file prefix to use for the bucket's access logs, option is ignored if logs_bucket is set to false.
   */
  readonly logsPrefix?: string;
}

/**
 * Interface for creating a ServerlessClamscan.
 */
export interface ServerlessClamscanProps {
  /**
   * An optional list of S3 buckets to configure for ClamAV Virus Scanning; buckets can be added later by calling addSourceBucket.
   */
  readonly buckets?: Bucket[];
  /**
   * The Lambda Destination for files marked 'CLEAN' or 'INFECTED' based on the ClamAV Virus scan or 'N/A' for scans triggered by S3 folder creation events marked (Default: Creates and publishes to a new Event Bridge Bus if unspecified).
   */
  readonly onResult?: IDestination;
  /**
   * The Lambda Destination for files that fail to scan and are marked 'ERROR' or stuck 'IN PROGRESS' due to a Lambda timeout (Default: Creates and publishes to a new SQS queue if unspecified).
   */
  readonly onError?: IDestination;
  /**
   * Whether or not to enable encryption on EFS filesystem (Default: enabled).
   */
  readonly efsEncryption?: boolean;
  /**
   * Whether or not to enable Access Logging for the Virus Definitions bucket, you can specify an existing bucket and prefix (Default: Creates a new S3 Bucket for access logs ).
   */
  readonly defsBucketAccessLogsConfig?: ServerlessClamscanLoggingProps;

  /**
   * You can specify an existing VPC (Default: Creates a VPC with isolated subnets).
   */
  readonly vpc?: Vpc;

  /**
  * You can specify an existing S3 Gateway enpoint (Default: Creates a new S3 Gateway enpoint).
  *
  * Only used if 'vpc' is supplied.
  */
  readonly s3GatewayVpcEndpoint?: GatewayVpcEndpoint;
}

/**
  An [aws-cdk](https://github.com/aws/aws-cdk) construct that uses [ClamAV®](https://www.clamav.net/).
  to scan objects in Amazon S3 for viruses. The construct provides a flexible interface for a system
  to act based on the results of a ClamAV virus scan.

  The construct creates a Lambda function with EFS integration to support larger files.
  A VPC with isolated subnets, a S3 Gateway endpoint will also be created.

  Additionally creates an twice-daily job to download the latest ClamAV definition files to the
  Virus Definitions S3 Bucket by utilizing an EventBridge rule and a Lambda function and
  publishes CloudWatch Metrics to the 'serverless-clamscan' namespace.

  __Important O&M__:
  When ClamAV publishes updates to the scanner you will see “Your ClamAV installation is OUTDATED” in your scan results.
  While the construct creates a system to keep the database definitions up to date, you must update the scanner to
  detect all the latest Viruses.

  Update the docker images of the Lambda functions with the latest version of ClamAV by re-running `cdk deploy`.

  Successful Scan Event format
  ```json
  {
     "source": "serverless-clamscan",
     "input_bucket": <input_bucket_name>,
     "input_key": <object_key>,
     "status": <"CLEAN"|"INFECTED"|"N/A">,
     "message": <scan_summary>,
   }
  ```

  Note: The Virus Definitions bucket policy will likely cause a deletion error if you choose to delete
  the stack associated in the construct. However since the bucket itself gets deleted, you can delete
  the stack again to resolve the error.
 */
export class ServerlessClamscan extends Construct {
  /**
    The Lambda Destination for failed on erred scans [ERROR, IN PROGRESS (If error is due to Lambda timeout)].
   */
  public readonly errorDest: IDestination;

  /**
    The Lambda Destination for completed ClamAV scans [CLEAN, INFECTED].
   */
  public readonly resultDest: IDestination;

  /**
    Conditional: The SQS Queue for erred scans if a failure (onError) destination was not specified.
   */
  public readonly errorQueue?: Queue;

  /**
    Conditional: The SQS Dead Letter Queue for the errorQueue if a failure (onError) destination was not specified.
   */
  public readonly errorDeadLetterQueue?: Queue;

  /**
    Conditional: The Event Bridge Bus for completed ClamAV scans if a success (onResult) destination was not specified.
   */
  public readonly resultBus?: EventBus;

  /**
    Conditional: An Event Bridge Rule for files that are marked 'CLEAN' by ClamAV if a success destination was not specified.
   */
  public readonly cleanRule?: Rule;

  /**
    Conditional: An Event Bridge Rule for files that are marked 'INFECTED' by ClamAV if a success destination was not specified.
   */
  public readonly infectedRule?: Rule;

  /**
    Conditional: The Bucket for access logs for the virus definitions bucket if logging is enabled (defsBucketAccessLogsConfig).
   */
  public readonly defsAccessLogsBucket?: Bucket;

  private _vpc: Vpc;
  private _scanFunction: DockerImageFunction;
  private _s3Gw: GatewayVpcEndpoint;
  private _efsRootPath = '/lambda';
  private _efsMountPath = `/mnt${this._efsRootPath}`;
  private _efsDefsPath = 'virus_database/';

  /**
   * Creates a ServerlessClamscan construct.
   * @param scope The parent creating construct (usually `this`).
   * @param id The construct's name.
   * @param props A `ServerlessClamscanProps` interface.
   */
  constructor(scope: Construct, id: string, props: ServerlessClamscanProps) {
    super(scope, id);

    if (!props.onResult) {
      this.resultBus = new EventBus(this, 'ScanResultBus');
      this.resultDest = new EventBridgeDestination(this.resultBus);
      this.infectedRule = new Rule(this, 'InfectedRule', {
        eventBus: this.resultBus,
        description: 'Event for when a file is marked INFECTED',
        eventPattern: {
          detail: {
            responsePayload: {
              source: ['serverless-clamscan'],
              status: ['INFECTED'],
            },
          },
        },
      });
      this.cleanRule = new Rule(this, 'CleanRule', {
        eventBus: this.resultBus,
        description: 'Event for when a file is marked CLEAN',
        eventPattern: {
          detail: {
            responsePayload: {
              source: ['serverless-clamscan'],
              status: ['CLEAN'],
            },
          },
        },
      });
    } else {
      this.resultDest = props.onResult;
    }

    if (!props.onError) {
      this.errorDeadLetterQueue = new Queue(this, 'ScanErrorDeadLetterQueue', {
        encryption: QueueEncryption.KMS_MANAGED,
      });
      this.errorQueue = new Queue(this, 'ScanErrorQueue', {
        encryption: QueueEncryption.KMS_MANAGED,
        deadLetterQueue: {
          maxReceiveCount: 3,
          queue: this.errorDeadLetterQueue,
        },
      });
      this.errorDest = new SqsDestination(this.errorQueue);
      const cfnDlq = this.errorDeadLetterQueue.node.defaultChild as CfnQueue;
      cfnDlq.addMetadata('cdk_nag', {
        rules_to_suppress: [
          { id: 'AwsSolutions-SQS3', reason: 'This queue is a DLQ.' },
        ],
      });
    } else {
      this.errorDest = props.onError;
    }

    if (props.vpc) {
      this._vpc = props.vpc;
    } else {
      this._vpc = new Vpc(this, 'ScanVPC', {
        subnetConfiguration: [
          {
            subnetType: SubnetType.PRIVATE_ISOLATED,
            name: 'Isolated',
          },
        ],
      });

      this._vpc.addFlowLog('FlowLogs');
    }

    if (props.s3GatewayVpcEndpoint) {
      if (!props.vpc) {
        throw new Error('\'s3GatewayVpcEndpoint\' property cannot be used if \'vpc\' is not specified.');
      }
      this._s3Gw = props.s3GatewayVpcEndpoint;
    } else {
      this._s3Gw = this._vpc.addGatewayEndpoint('S3Endpoint', {
        service: GatewayVpcEndpointAwsService.S3,
      });
    }

    const fileSystem = new FileSystem(this, 'ScanFileSystem', {
      vpc: this._vpc,
      encrypted: props.efsEncryption === false ? false : true,
      lifecyclePolicy: LifecyclePolicy.AFTER_7_DAYS,
      performanceMode: PerformanceMode.GENERAL_PURPOSE,
      removalPolicy: RemovalPolicy.DESTROY,
      securityGroup: new SecurityGroup(this, 'ScanFileSystemSecurityGroup', {
        vpc: this._vpc,
        allowAllOutbound: false,
      }),
    });

    const lambda_ap = fileSystem.addAccessPoint('ScanLambdaAP', {
      createAcl: {
        ownerGid: '1000',
        ownerUid: '1000',
        permissions: '755',
      },
      posixUser: {
        gid: '1000',
        uid: '1000',
      },
      path: this._efsRootPath,
    });

    const logs_bucket = props.defsBucketAccessLogsConfig?.logsBucket;
    const logs_bucket_prefix = props.defsBucketAccessLogsConfig?.logsPrefix;
    if (logs_bucket === true || logs_bucket === undefined) {
      this.defsAccessLogsBucket = new Bucket(
        this,
        'VirusDefsAccessLogsBucket',
        {
          encryption: BucketEncryption.S3_MANAGED,
          removalPolicy: RemovalPolicy.RETAIN,
          serverAccessLogsPrefix: 'access-logs-bucket-logs',
          blockPublicAccess: {
            blockPublicAcls: true,
            blockPublicPolicy: true,
            ignorePublicAcls: true,
            restrictPublicBuckets: true,
          },
        },
      );
      this.defsAccessLogsBucket.addToResourcePolicy(
        new PolicyStatement({
          effect: Effect.DENY,
          actions: ['s3:*'],
          resources: [
            this.defsAccessLogsBucket.arnForObjects('*'),
            this.defsAccessLogsBucket.bucketArn,
          ],
          principals: [new AnyPrincipal()],
          conditions: {
            Bool: {
              'aws:SecureTransport': false,
            },
          },
        }),
      );
    } else if (logs_bucket != false) {
      this.defsAccessLogsBucket = logs_bucket;
    }

    const defs_bucket = new Bucket(this, 'VirusDefsBucket', {
      encryption: BucketEncryption.S3_MANAGED,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      serverAccessLogsBucket: this.defsAccessLogsBucket,
      serverAccessLogsPrefix:
        logs_bucket === false ? undefined : logs_bucket_prefix,
      blockPublicAccess: {
        blockPublicAcls: true,
        blockPublicPolicy: true,
        ignorePublicAcls: true,
        restrictPublicBuckets: true,
      },
    });

    defs_bucket.addToResourcePolicy(
      new PolicyStatement({
        effect: Effect.DENY,
        actions: ['s3:*'],
        resources: [defs_bucket.arnForObjects('*'), defs_bucket.bucketArn],
        principals: [new AnyPrincipal()],
        conditions: {
          Bool: {
            'aws:SecureTransport': false,
          },
        },
      }),
    );
    defs_bucket.addToResourcePolicy(
      new PolicyStatement({
        effect: Effect.ALLOW,
        actions: ['s3:GetObject', 's3:ListBucket'],
        resources: [defs_bucket.arnForObjects('*'), defs_bucket.bucketArn],
        principals: [new AnyPrincipal()],
        conditions: {
          StringEquals: {
            'aws:SourceVpce': this._s3Gw.vpcEndpointId,
          },
        },
      }),
    );
    defs_bucket.addToResourcePolicy(
      new PolicyStatement({
        effect: Effect.DENY,
        actions: ['s3:PutBucketPolicy', 's3:DeleteBucketPolicy'],
        resources: [defs_bucket.bucketArn],
        notPrincipals: [new AccountRootPrincipal()],
      }),
    );
    this._s3Gw.addToPolicy(
      new PolicyStatement({
        effect: Effect.ALLOW,
        actions: ['s3:GetObject', 's3:ListBucket'],
        resources: [defs_bucket.arnForObjects('*'), defs_bucket.bucketArn],
        principals: [new AnyPrincipal()],
      }),
    );

    this._scanFunction = new DockerImageFunction(this, 'ServerlessClamscan', {
      code: DockerImageCode.fromImageAsset(
        path.join(__dirname, '../assets/lambda/code/scan'),
        {
          buildArgs: {
            // Only force update the docker layer cache once a day
            CACHE_DATE: new Date().toDateString(),
          },
          extraHash: Date.now().toString(),
        },
      ),
      onSuccess: this.resultDest,
      onFailure: this.errorDest,
      filesystem: LambdaFileSystem.fromEfsAccessPoint(
        lambda_ap,
        this._efsMountPath,
      ),
      vpc: this._vpc,
      vpcSubnets: { subnets: this._vpc.isolatedSubnets },
      allowAllOutbound: false,
      timeout: Duration.minutes(15),
      memorySize: 10240,
      environment: {
        EFS_MOUNT_PATH: this._efsMountPath,
        EFS_DEF_PATH: this._efsDefsPath,
        DEFS_URL: defs_bucket.virtualHostedUrlForObject(),
        POWERTOOLS_METRICS_NAMESPACE: 'serverless-clamscan',
        POWERTOOLS_SERVICE_NAME: 'virus-scan',
      },
    });
    if (this._scanFunction.role) {
      const cfnScanRole = this._scanFunction.role.node.defaultChild as CfnRole;
      cfnScanRole.addMetadata('cdk_nag', {
        rules_to_suppress: [
          {
            id: 'AwsSolutions-IAM4',
            reason:
              'The AWSLambdaBasicExecutionRole does not provide permissions beyond uploading logs to CloudWatch. The AWSLambdaVPCAccessExecutionRole is required for functions with VPC access to manage elastic network interfaces.',
          },
        ],
      });
      const cfnScanRoleChildren = this._scanFunction.role.node.children;
      for (const child of cfnScanRoleChildren) {
        const resource = child.node.defaultChild as CfnResource;
        if (resource != undefined && resource.cfnResourceType == 'AWS::IAM::Policy') {
          resource.addMetadata('cdk_nag', {
            rules_to_suppress: [
              {
                id: 'AwsSolutions-IAM5',
                reason:
                  'The EFS mount point permissions are controlled through a condition which limit the scope of the * resources.',
              },
            ],
          });
        }
      }
    }
    this._scanFunction.connections.allowToAnyIpv4(
      Port.tcp(443),
      'Allow outbound HTTPS traffic for S3 access.',
    );
    defs_bucket.grantRead(this._scanFunction);

    const download_defs = new DockerImageFunction(this, 'DownloadDefs', {
      code: DockerImageCode.fromImageAsset(
        path.join(__dirname, '../assets/lambda/code/download_defs'),
        {
          buildArgs: {
            // Only force update the docker layer cache once a day
            CACHE_DATE: new Date().toDateString(),
          },
          extraHash: Date.now().toString(),
        },
      ),
      timeout: Duration.minutes(5),
      memorySize: 1024,
      environment: {
        DEFS_BUCKET: defs_bucket.bucketName,
        POWERTOOLS_SERVICE_NAME: 'freshclam-update',
      },
    });
    const stack = Stack.of(this);

    if (download_defs.role) {
      const download_defs_role = `arn:${stack.partition}:sts::${stack.account}:assumed-role/${download_defs.role.roleName}/${download_defs.functionName}`;
      const download_defs_assumed_principal = new ArnPrincipal(
        download_defs_role,
      );
      defs_bucket.addToResourcePolicy(
        new PolicyStatement({
          effect: Effect.DENY,
          actions: ['s3:PutObject*'],
          resources: [defs_bucket.arnForObjects('*')],
          notPrincipals: [download_defs.role, download_defs_assumed_principal],
        }),
      );
      defs_bucket.grantReadWrite(download_defs);
      const cfnDownloadRole = download_defs.role.node.defaultChild as CfnRole;
      cfnDownloadRole.addMetadata('cdk_nag', {
        rules_to_suppress: [
          {
            id: 'AwsSolutions-IAM4',
            reason:
              'The AWSLambdaBasicExecutionRole does not provide permissions beyond uploading logs to CloudWatch.',
          },
        ],
      });
      const cfnDownloadRoleChildren = download_defs.role.node.children;
      for (const child of cfnDownloadRoleChildren) {
        const resource = child.node.defaultChild as CfnResource;
        if (resource != undefined && resource.cfnResourceType == 'AWS::IAM::Policy') {
          resource.addMetadata('cdk_nag', {
            rules_to_suppress: [
              {
                id: 'AwsSolutions-IAM5',
                reason:
                  'The function is allowed to perform operations on all prefixes in the specified bucket.',
              },
            ],
          });
        }
      }
    }

    new Rule(this, 'VirusDefsUpdateRule', {
      schedule: Schedule.rate(Duration.hours(12)),
      targets: [new LambdaFunction(download_defs)],
    });

    const init_defs_cr = new Function(this, 'InitDefs', {
      runtime: Runtime.PYTHON_3_8,
      code: Code.fromAsset(
        path.join(__dirname, '../assets/lambda/code/initialize_defs_cr'),
      ),
      handler: 'lambda.lambda_handler',
      timeout: Duration.minutes(5),
    });
    download_defs.grantInvoke(init_defs_cr);
    if (init_defs_cr.role) {
      const cfnScanRole = init_defs_cr.role.node.defaultChild as CfnRole;
      cfnScanRole.addMetadata('cdk_nag', {
        rules_to_suppress: [
          {
            id: 'AwsSolutions-IAM4',
            reason:
              'The AWSLambdaBasicExecutionRole does not provide permissions beyond uploading logs to CloudWatch.',
          },
        ],
      });
    }
    new CustomResource(this, 'InitDefsCr', {
      serviceToken: init_defs_cr.functionArn,
      properties: {
        FnName: download_defs.functionName,
      },
    });

    if (props.buckets) {
      props.buckets.forEach((bucket) => {
        this.addSourceBucket(bucket);
      });
    }
  }

  /**
   * Sets the specified S3 Bucket as a s3:ObjectCreate* for the ClamAV function.
     Grants the ClamAV function permissions to get and tag objects.
     Adds a bucket policy to disallow GetObject operations on files that are tagged 'IN PROGRESS', 'INFECTED', or 'ERROR'.
   * @param bucket The bucket to add the scanning bucket policy and s3:ObjectCreate* trigger to.
   */
  addSourceBucket(bucket: Bucket) {
    this._scanFunction.addEventSource(
      new S3EventSource(bucket, { events: [EventType.OBJECT_CREATED] }),
    );
    bucket.grantRead(this._scanFunction);
    this._scanFunction.addToRolePolicy(
      new PolicyStatement({
        effect: Effect.ALLOW,
        actions: ['s3:PutObjectTagging', 's3:PutObjectVersionTagging'],
        resources: [bucket.arnForObjects('*')],
      }),
    );

    if (this._scanFunction.role) {
      const stack = Stack.of(this);
      const scan_assumed_role = `arn:${stack.partition}:sts::${stack.account}:assumed-role/${this._scanFunction.role.roleName}/${this._scanFunction.functionName}`;
      const scan_assumed_principal = new ArnPrincipal(scan_assumed_role);
      this._s3Gw.addToPolicy(
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ['s3:GetObject*', 's3:GetBucket*', 's3:List*'],
          resources: [bucket.bucketArn, bucket.arnForObjects('*')],
          principals: [this._scanFunction.role, scan_assumed_principal],
        }),
      );
      this._s3Gw.addToPolicy(
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ['s3:PutObjectTagging', 's3:PutObjectVersionTagging'],
          resources: [bucket.arnForObjects('*')],
          principals: [this._scanFunction.role, scan_assumed_principal],
        }),
      );

      // Need the assumed role for the not Principal Action with Lambda
      bucket.addToResourcePolicy(
        new PolicyStatement({
          effect: Effect.DENY,
          actions: ['s3:GetObject'],
          resources: [bucket.arnForObjects('*')],
          notPrincipals: [this._scanFunction.role, scan_assumed_principal],
          conditions: {
            StringEquals: {
              's3:ExistingObjectTag/scan-status': [
                'IN PROGRESS',
                'INFECTED',
                'ERROR',
              ],
            },
          },
        }),
      );
    }
  }
}
