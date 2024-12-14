# API Reference <a name="API Reference" id="api-reference"></a>

## Constructs <a name="Constructs" id="Constructs"></a>

### ServerlessClamscan <a name="ServerlessClamscan" id="cdk-serverless-clamscan.ServerlessClamscan"></a>

An [aws-cdk](https://github.com/aws/aws-cdk) construct that uses [ClamAV®](https://www.clamav.net/). to scan objects in Amazon S3 for viruses. The construct provides a flexible interface for a system to act based on the results of a ClamAV virus scan.

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

#### Initializers <a name="Initializers" id="cdk-serverless-clamscan.ServerlessClamscan.Initializer"></a>

```typescript
import { ServerlessClamscan } from 'cdk-serverless-clamscan'

new ServerlessClamscan(scope: Construct, id: string, props: ServerlessClamscanProps)
```

| **Name** | **Type** | **Description** |
| --- | --- | --- |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.Initializer.parameter.scope">scope</a></code> | <code>constructs.Construct</code> | The parent creating construct (usually `this`). |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.Initializer.parameter.id">id</a></code> | <code>string</code> | The construct's name. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.Initializer.parameter.props">props</a></code> | <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps">ServerlessClamscanProps</a></code> | A `ServerlessClamscanProps` interface. |

---

##### `scope`<sup>Required</sup> <a name="scope" id="cdk-serverless-clamscan.ServerlessClamscan.Initializer.parameter.scope"></a>

- *Type:* constructs.Construct

The parent creating construct (usually `this`).

---

##### `id`<sup>Required</sup> <a name="id" id="cdk-serverless-clamscan.ServerlessClamscan.Initializer.parameter.id"></a>

- *Type:* string

The construct's name.

---

##### `props`<sup>Required</sup> <a name="props" id="cdk-serverless-clamscan.ServerlessClamscan.Initializer.parameter.props"></a>

- *Type:* <a href="#cdk-serverless-clamscan.ServerlessClamscanProps">ServerlessClamscanProps</a>

A `ServerlessClamscanProps` interface.

---

#### Methods <a name="Methods" id="Methods"></a>

| **Name** | **Description** |
| --- | --- |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.toString">toString</a></code> | Returns a string representation of this construct. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.addSourceBucket">addSourceBucket</a></code> | Sets the specified S3 Bucket as a s3:ObjectCreate* for the ClamAV function. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.getPolicyStatementForBucket">getPolicyStatementForBucket</a></code> | Returns the statement that should be added to the bucket policy in order to prevent objects to be accessed when they are not clean or there have been scanning errors: this policy should be added manually if external buckets are passed to addSourceBucket(). |

---

##### `toString` <a name="toString" id="cdk-serverless-clamscan.ServerlessClamscan.toString"></a>

```typescript
public toString(): string
```

Returns a string representation of this construct.

##### `addSourceBucket` <a name="addSourceBucket" id="cdk-serverless-clamscan.ServerlessClamscan.addSourceBucket"></a>

```typescript
public addSourceBucket(bucket: IBucket): void
```

Sets the specified S3 Bucket as a s3:ObjectCreate* for the ClamAV function.

Grants the ClamAV function permissions to get and tag objects.
Adds a bucket policy to disallow GetObject operations on files that are tagged 'IN PROGRESS', 'INFECTED', or 'ERROR'.

###### `bucket`<sup>Required</sup> <a name="bucket" id="cdk-serverless-clamscan.ServerlessClamscan.addSourceBucket.parameter.bucket"></a>

- *Type:* aws-cdk-lib.aws_s3.IBucket

The bucket to add the scanning bucket policy and s3:ObjectCreate* trigger to.

---

##### `getPolicyStatementForBucket` <a name="getPolicyStatementForBucket" id="cdk-serverless-clamscan.ServerlessClamscan.getPolicyStatementForBucket"></a>

```typescript
public getPolicyStatementForBucket(bucket: IBucket): PolicyStatement
```

Returns the statement that should be added to the bucket policy in order to prevent objects to be accessed when they are not clean or there have been scanning errors: this policy should be added manually if external buckets are passed to addSourceBucket().

###### `bucket`<sup>Required</sup> <a name="bucket" id="cdk-serverless-clamscan.ServerlessClamscan.getPolicyStatementForBucket.parameter.bucket"></a>

- *Type:* aws-cdk-lib.aws_s3.IBucket

The bucket which you need to protect with the policy.

---

#### Static Functions <a name="Static Functions" id="Static Functions"></a>

| **Name** | **Description** |
| --- | --- |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.isConstruct">isConstruct</a></code> | Checks if `x` is a construct. |

---

##### ~~`isConstruct`~~ <a name="isConstruct" id="cdk-serverless-clamscan.ServerlessClamscan.isConstruct"></a>

```typescript
import { ServerlessClamscan } from 'cdk-serverless-clamscan'

ServerlessClamscan.isConstruct(x: any)
```

Checks if `x` is a construct.

###### `x`<sup>Required</sup> <a name="x" id="cdk-serverless-clamscan.ServerlessClamscan.isConstruct.parameter.x"></a>

- *Type:* any

Any object.

---

#### Properties <a name="Properties" id="Properties"></a>

| **Name** | **Type** | **Description** |
| --- | --- | --- |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.node">node</a></code> | <code>constructs.Node</code> | The tree node. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.errorDest">errorDest</a></code> | <code>aws-cdk-lib.aws_lambda.IDestination</code> | The Lambda Destination for failed on erred scans [ERROR, IN PROGRESS (If error is due to Lambda timeout)]. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.resultDest">resultDest</a></code> | <code>aws-cdk-lib.aws_lambda.IDestination</code> | The Lambda Destination for completed ClamAV scans [CLEAN, INFECTED]. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.scanAssumedPrincipal">scanAssumedPrincipal</a></code> | <code>aws-cdk-lib.aws_iam.ArnPrincipal</code> | *No description.* |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.cleanRule">cleanRule</a></code> | <code>aws-cdk-lib.aws_events.Rule</code> | Conditional: An Event Bridge Rule for files that are marked 'CLEAN' by ClamAV if a success destination was not specified. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.defsAccessLogsBucket">defsAccessLogsBucket</a></code> | <code>aws-cdk-lib.aws_s3.IBucket</code> | Conditional: The Bucket for access logs for the virus definitions bucket if logging is enabled (defsBucketAccessLogsConfig). |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.errorDeadLetterQueue">errorDeadLetterQueue</a></code> | <code>aws-cdk-lib.aws_sqs.Queue</code> | Conditional: The SQS Dead Letter Queue for the errorQueue if a failure (onError) destination was not specified. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.errorQueue">errorQueue</a></code> | <code>aws-cdk-lib.aws_sqs.Queue</code> | Conditional: The SQS Queue for erred scans if a failure (onError) destination was not specified. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.infectedRule">infectedRule</a></code> | <code>aws-cdk-lib.aws_events.Rule</code> | Conditional: An Event Bridge Rule for files that are marked 'INFECTED' by ClamAV if a success destination was not specified. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.resultBus">resultBus</a></code> | <code>aws-cdk-lib.aws_events.EventBus</code> | Conditional: The Event Bridge Bus for completed ClamAV scans if a success (onResult) destination was not specified. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscan.property.useImportedBuckets">useImportedBuckets</a></code> | <code>boolean</code> | Conditional: When true, the user accepted the responsibility for using imported buckets. |

---

##### `node`<sup>Required</sup> <a name="node" id="cdk-serverless-clamscan.ServerlessClamscan.property.node"></a>

```typescript
public readonly node: Node;
```

- *Type:* constructs.Node

The tree node.

---

##### `errorDest`<sup>Required</sup> <a name="errorDest" id="cdk-serverless-clamscan.ServerlessClamscan.property.errorDest"></a>

```typescript
public readonly errorDest: IDestination;
```

- *Type:* aws-cdk-lib.aws_lambda.IDestination

The Lambda Destination for failed on erred scans [ERROR, IN PROGRESS (If error is due to Lambda timeout)].

---

##### `resultDest`<sup>Required</sup> <a name="resultDest" id="cdk-serverless-clamscan.ServerlessClamscan.property.resultDest"></a>

```typescript
public readonly resultDest: IDestination;
```

- *Type:* aws-cdk-lib.aws_lambda.IDestination

The Lambda Destination for completed ClamAV scans [CLEAN, INFECTED].

---

##### `scanAssumedPrincipal`<sup>Required</sup> <a name="scanAssumedPrincipal" id="cdk-serverless-clamscan.ServerlessClamscan.property.scanAssumedPrincipal"></a>

```typescript
public readonly scanAssumedPrincipal: ArnPrincipal;
```

- *Type:* aws-cdk-lib.aws_iam.ArnPrincipal

---

##### `cleanRule`<sup>Optional</sup> <a name="cleanRule" id="cdk-serverless-clamscan.ServerlessClamscan.property.cleanRule"></a>

```typescript
public readonly cleanRule: Rule;
```

- *Type:* aws-cdk-lib.aws_events.Rule

Conditional: An Event Bridge Rule for files that are marked 'CLEAN' by ClamAV if a success destination was not specified.

---

##### `defsAccessLogsBucket`<sup>Optional</sup> <a name="defsAccessLogsBucket" id="cdk-serverless-clamscan.ServerlessClamscan.property.defsAccessLogsBucket"></a>

```typescript
public readonly defsAccessLogsBucket: IBucket;
```

- *Type:* aws-cdk-lib.aws_s3.IBucket

Conditional: The Bucket for access logs for the virus definitions bucket if logging is enabled (defsBucketAccessLogsConfig).

---

##### `errorDeadLetterQueue`<sup>Optional</sup> <a name="errorDeadLetterQueue" id="cdk-serverless-clamscan.ServerlessClamscan.property.errorDeadLetterQueue"></a>

```typescript
public readonly errorDeadLetterQueue: Queue;
```

- *Type:* aws-cdk-lib.aws_sqs.Queue

Conditional: The SQS Dead Letter Queue for the errorQueue if a failure (onError) destination was not specified.

---

##### `errorQueue`<sup>Optional</sup> <a name="errorQueue" id="cdk-serverless-clamscan.ServerlessClamscan.property.errorQueue"></a>

```typescript
public readonly errorQueue: Queue;
```

- *Type:* aws-cdk-lib.aws_sqs.Queue

Conditional: The SQS Queue for erred scans if a failure (onError) destination was not specified.

---

##### `infectedRule`<sup>Optional</sup> <a name="infectedRule" id="cdk-serverless-clamscan.ServerlessClamscan.property.infectedRule"></a>

```typescript
public readonly infectedRule: Rule;
```

- *Type:* aws-cdk-lib.aws_events.Rule

Conditional: An Event Bridge Rule for files that are marked 'INFECTED' by ClamAV if a success destination was not specified.

---

##### `resultBus`<sup>Optional</sup> <a name="resultBus" id="cdk-serverless-clamscan.ServerlessClamscan.property.resultBus"></a>

```typescript
public readonly resultBus: EventBus;
```

- *Type:* aws-cdk-lib.aws_events.EventBus

Conditional: The Event Bridge Bus for completed ClamAV scans if a success (onResult) destination was not specified.

---

##### `useImportedBuckets`<sup>Optional</sup> <a name="useImportedBuckets" id="cdk-serverless-clamscan.ServerlessClamscan.property.useImportedBuckets"></a>

```typescript
public readonly useImportedBuckets: boolean;
```

- *Type:* boolean

Conditional: When true, the user accepted the responsibility for using imported buckets.

---


## Structs <a name="Structs" id="Structs"></a>

### ServerlessClamscanLoggingProps <a name="ServerlessClamscanLoggingProps" id="cdk-serverless-clamscan.ServerlessClamscanLoggingProps"></a>

Interface for ServerlessClamscan Virus Definitions S3 Bucket Logging.

#### Initializer <a name="Initializer" id="cdk-serverless-clamscan.ServerlessClamscanLoggingProps.Initializer"></a>

```typescript
import { ServerlessClamscanLoggingProps } from 'cdk-serverless-clamscan'

const serverlessClamscanLoggingProps: ServerlessClamscanLoggingProps = { ... }
```

#### Properties <a name="Properties" id="Properties"></a>

| **Name** | **Type** | **Description** |
| --- | --- | --- |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanLoggingProps.property.logsBucket">logsBucket</a></code> | <code>boolean \| aws-cdk-lib.aws_s3.IBucket</code> | Destination bucket for the server access logs (Default: Creates a new S3 Bucket for access logs). |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanLoggingProps.property.logsPrefix">logsPrefix</a></code> | <code>string</code> | Optional log file prefix to use for the bucket's access logs, option is ignored if logs_bucket is set to false. |

---

##### `logsBucket`<sup>Optional</sup> <a name="logsBucket" id="cdk-serverless-clamscan.ServerlessClamscanLoggingProps.property.logsBucket"></a>

```typescript
public readonly logsBucket: boolean | IBucket;
```

- *Type:* boolean | aws-cdk-lib.aws_s3.IBucket

Destination bucket for the server access logs (Default: Creates a new S3 Bucket for access logs).

---

##### `logsPrefix`<sup>Optional</sup> <a name="logsPrefix" id="cdk-serverless-clamscan.ServerlessClamscanLoggingProps.property.logsPrefix"></a>

```typescript
public readonly logsPrefix: string;
```

- *Type:* string

Optional log file prefix to use for the bucket's access logs, option is ignored if logs_bucket is set to false.

---

### ServerlessClamscanProps <a name="ServerlessClamscanProps" id="cdk-serverless-clamscan.ServerlessClamscanProps"></a>

Interface for creating a ServerlessClamscan.

#### Initializer <a name="Initializer" id="cdk-serverless-clamscan.ServerlessClamscanProps.Initializer"></a>

```typescript
import { ServerlessClamscanProps } from 'cdk-serverless-clamscan'

const serverlessClamscanProps: ServerlessClamscanProps = { ... }
```

#### Properties <a name="Properties" id="Properties"></a>

| **Name** | **Type** | **Description** |
| --- | --- | --- |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.acceptResponsibilityForUsingImportedBucket">acceptResponsibilityForUsingImportedBucket</a></code> | <code>boolean</code> | Allows the use of imported buckets. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.buckets">buckets</a></code> | <code>aws-cdk-lib.aws_s3.IBucket[]</code> | An optional list of S3 buckets to configure for ClamAV Virus Scanning; |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.defsBucketAccessLogsConfig">defsBucketAccessLogsConfig</a></code> | <code><a href="#cdk-serverless-clamscan.ServerlessClamscanLoggingProps">ServerlessClamscanLoggingProps</a></code> | Whether or not to enable Access Logging for the Virus Definitions bucket, you can specify an existing bucket and prefix (Default: Creates a new S3 Bucket for access logs). |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.defsBucketAllowPolicyMutation">defsBucketAllowPolicyMutation</a></code> | <code>boolean</code> | Allow for non-root users to modify/delete the bucket policy on the Virus Definitions bucket. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.efsEncryption">efsEncryption</a></code> | <code>boolean</code> | Whether or not to enable encryption on EFS filesystem (Default: enabled). |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.efsPerformanceMode">efsPerformanceMode</a></code> | <code>aws-cdk-lib.aws_efs.PerformanceMode</code> | Set the performance mode of the EFS file system (Default: GENERAL_PURPOSE). |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.efsProvisionedThroughputPerSecond">efsProvisionedThroughputPerSecond</a></code> | <code>aws-cdk-lib.Size</code> | Provisioned throughput for the EFS file system. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.efsThroughputMode">efsThroughputMode</a></code> | <code>aws-cdk-lib.aws_efs.ThroughputMode</code> | Set the throughput mode of the EFS file system (Default: BURSTING). |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.onError">onError</a></code> | <code>aws-cdk-lib.aws_lambda.IDestination</code> | The Lambda Destination for files that fail to scan and are marked 'ERROR' or stuck 'IN PROGRESS' due to a Lambda timeout (Default: Creates and publishes to a new SQS queue if unspecified). |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.onResult">onResult</a></code> | <code>aws-cdk-lib.aws_lambda.IDestination</code> | The Lambda Destination for files marked 'CLEAN' or 'INFECTED' based on the ClamAV Virus scan or 'N/A' for scans triggered by S3 folder creation events marked (Default: Creates and publishes to a new Event Bridge Bus if unspecified). |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.reservedConcurrency">reservedConcurrency</a></code> | <code>number</code> | Optionally set a reserved concurrency for the virus scanning Lambda. |
| <code><a href="#cdk-serverless-clamscan.ServerlessClamscanProps.property.scanFunctionMemorySize">scanFunctionMemorySize</a></code> | <code>number</code> | Optionally set the memory allocation for the scan function. |

---

##### `acceptResponsibilityForUsingImportedBucket`<sup>Optional</sup> <a name="acceptResponsibilityForUsingImportedBucket" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.acceptResponsibilityForUsingImportedBucket"></a>

```typescript
public readonly acceptResponsibilityForUsingImportedBucket: boolean;
```

- *Type:* boolean

Allows the use of imported buckets.

When using imported buckets the user is responsible for adding the required policy statement to the bucket policy: `getPolicyStatementForBucket()` can be used to retrieve the policy statement required by the solution.

---

##### `buckets`<sup>Optional</sup> <a name="buckets" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.buckets"></a>

```typescript
public readonly buckets: IBucket[];
```

- *Type:* aws-cdk-lib.aws_s3.IBucket[]

An optional list of S3 buckets to configure for ClamAV Virus Scanning;

buckets can be added later by calling addSourceBucket.

---

##### `defsBucketAccessLogsConfig`<sup>Optional</sup> <a name="defsBucketAccessLogsConfig" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.defsBucketAccessLogsConfig"></a>

```typescript
public readonly defsBucketAccessLogsConfig: ServerlessClamscanLoggingProps;
```

- *Type:* <a href="#cdk-serverless-clamscan.ServerlessClamscanLoggingProps">ServerlessClamscanLoggingProps</a>

Whether or not to enable Access Logging for the Virus Definitions bucket, you can specify an existing bucket and prefix (Default: Creates a new S3 Bucket for access logs).

---

##### `defsBucketAllowPolicyMutation`<sup>Optional</sup> <a name="defsBucketAllowPolicyMutation" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.defsBucketAllowPolicyMutation"></a>

```typescript
public readonly defsBucketAllowPolicyMutation: boolean;
```

- *Type:* boolean
- *Default:* false

Allow for non-root users to modify/delete the bucket policy on the Virus Definitions bucket.

Warning: changing this flag from 'false' to 'true' on existing deployments will cause updates to fail.

---

##### `efsEncryption`<sup>Optional</sup> <a name="efsEncryption" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.efsEncryption"></a>

```typescript
public readonly efsEncryption: boolean;
```

- *Type:* boolean

Whether or not to enable encryption on EFS filesystem (Default: enabled).

---

##### `efsPerformanceMode`<sup>Optional</sup> <a name="efsPerformanceMode" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.efsPerformanceMode"></a>

```typescript
public readonly efsPerformanceMode: PerformanceMode;
```

- *Type:* aws-cdk-lib.aws_efs.PerformanceMode

Set the performance mode of the EFS file system (Default: GENERAL_PURPOSE).

---

##### `efsProvisionedThroughputPerSecond`<sup>Optional</sup> <a name="efsProvisionedThroughputPerSecond" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.efsProvisionedThroughputPerSecond"></a>

```typescript
public readonly efsProvisionedThroughputPerSecond: Size;
```

- *Type:* aws-cdk-lib.Size

Provisioned throughput for the EFS file system.

This is a required property if the throughput mode is set to PROVISIONED. Must be at least 1MiB/s (Default: none).

---

##### `efsThroughputMode`<sup>Optional</sup> <a name="efsThroughputMode" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.efsThroughputMode"></a>

```typescript
public readonly efsThroughputMode: ThroughputMode;
```

- *Type:* aws-cdk-lib.aws_efs.ThroughputMode

Set the throughput mode of the EFS file system (Default: BURSTING).

---

##### `onError`<sup>Optional</sup> <a name="onError" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.onError"></a>

```typescript
public readonly onError: IDestination;
```

- *Type:* aws-cdk-lib.aws_lambda.IDestination

The Lambda Destination for files that fail to scan and are marked 'ERROR' or stuck 'IN PROGRESS' due to a Lambda timeout (Default: Creates and publishes to a new SQS queue if unspecified).

---

##### `onResult`<sup>Optional</sup> <a name="onResult" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.onResult"></a>

```typescript
public readonly onResult: IDestination;
```

- *Type:* aws-cdk-lib.aws_lambda.IDestination

The Lambda Destination for files marked 'CLEAN' or 'INFECTED' based on the ClamAV Virus scan or 'N/A' for scans triggered by S3 folder creation events marked (Default: Creates and publishes to a new Event Bridge Bus if unspecified).

---

##### `reservedConcurrency`<sup>Optional</sup> <a name="reservedConcurrency" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.reservedConcurrency"></a>

```typescript
public readonly reservedConcurrency: number;
```

- *Type:* number

Optionally set a reserved concurrency for the virus scanning Lambda.

> [https://docs.aws.amazon.com/lambda/latest/operatorguide/reserved-concurrency.html](https://docs.aws.amazon.com/lambda/latest/operatorguide/reserved-concurrency.html)

---

##### `scanFunctionMemorySize`<sup>Optional</sup> <a name="scanFunctionMemorySize" id="cdk-serverless-clamscan.ServerlessClamscanProps.property.scanFunctionMemorySize"></a>

```typescript
public readonly scanFunctionMemorySize: number;
```

- *Type:* number

Optionally set the memory allocation for the scan function.

Note that low memory allocations may cause errors. (Default: 10240).

> [https://docs.aws.amazon.com/lambda/latest/operatorguide/computing-power.html](https://docs.aws.amazon.com/lambda/latest/operatorguide/computing-power.html)

---



