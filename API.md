# API Reference

**Classes**

Name|Description
----|-----------
[ServerlessClamscan](#cdk-serverless-clamscan-serverlessclamscan)|An [aws-cdk](https://github.com/aws/aws-cdk) construct that uses [ClamAV®](https://www.clamav.net/). to scan objects in Amazon S3 for viruses. The construct provides a flexible interface for a system to act based on the results of a ClamAV virus scan.


**Structs**

Name|Description
----|-----------
[ServerlessClamscanLoggingProps](#cdk-serverless-clamscan-serverlessclamscanloggingprops)|Interface for ServerlessClamscan Virus Definitions S3 Bucket Logging.
[ServerlessClamscanProps](#cdk-serverless-clamscan-serverlessclamscanprops)|Interface for creating a ServerlessClamscan.



## class ServerlessClamscan  <a id="cdk-serverless-clamscan-serverlessclamscan"></a>

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

__Implements__: [IConstruct](#constructs-iconstruct), [IDependable](#constructs-idependable)
__Extends__: [Construct](#constructs-construct)

### Initializer


Creates a ServerlessClamscan construct.

```ts
new ServerlessClamscan(scope: Construct, id: string, props: ServerlessClamscanProps)
```

* **scope** (<code>[Construct](#constructs-construct)</code>)  The parent creating construct (usually `this`).
* **id** (<code>string</code>)  The construct's name.
* **props** (<code>[ServerlessClamscanProps](#cdk-serverless-clamscan-serverlessclamscanprops)</code>)  A `ServerlessClamscanProps` interface.
  * **acceptResponsibilityForUsingImportedBucket** (<code>boolean</code>)  Allows the use of imported buckets. __*Optional*__
  * **buckets** (<code>Array<[aws_s3.IBucket](#aws-cdk-lib-aws-s3-ibucket)></code>)  An optional list of S3 buckets to configure for ClamAV Virus Scanning; __*Optional*__
  * **defsBucketAccessLogsConfig** (<code>[ServerlessClamscanLoggingProps](#cdk-serverless-clamscan-serverlessclamscanloggingprops)</code>)  Whether or not to enable Access Logging for the Virus Definitions bucket, you can specify an existing bucket and prefix (Default: Creates a new S3 Bucket for access logs). __*Optional*__
  * **dontPreventAccessBeforeScan** (<code>boolean</code>)  When enabled the bucket policy to block access to the file before until scanning completes is not applied. __*Optional*__
  * **efsEncryption** (<code>boolean</code>)  Whether or not to enable encryption on EFS filesystem (Default: enabled). __*Optional*__
  * **efsPerformanceMode** (<code>[aws_efs.PerformanceMode](#aws-cdk-lib-aws-efs-performancemode)</code>)  Set the performance mode of the EFS file system (Default: GENERAL_PURPOSE). __*Optional*__
  * **onError** (<code>[aws_lambda.IDestination](#aws-cdk-lib-aws-lambda-idestination)</code>)  The Lambda Destination for files that fail to scan and are marked 'ERROR' or stuck 'IN PROGRESS' due to a Lambda timeout (Default: Creates and publishes to a new SQS queue if unspecified). __*Optional*__
  * **onResult** (<code>[aws_lambda.IDestination](#aws-cdk-lib-aws-lambda-idestination)</code>)  The Lambda Destination for files marked 'CLEAN' or 'INFECTED' based on the ClamAV Virus scan or 'N/A' for scans triggered by S3 folder creation events marked (Default: Creates and publishes to a new Event Bridge Bus if unspecified). __*Optional*__
  * **reservedConcurrency** (<code>number</code>)  Optionally set a reserved concurrency for the virus scanning Lambda. __*Optional*__
  * **scanFunctionMemorySize** (<code>number</code>)  Optionally set the memory allocation for the scan function. __*Optional*__



### Properties


Name | Type | Description 
-----|------|-------------
**errorDest** | <code>[aws_lambda.IDestination](#aws-cdk-lib-aws-lambda-idestination)</code> | The Lambda Destination for failed on erred scans [ERROR, IN PROGRESS (If error is due to Lambda timeout)].
**props** | <code>[ServerlessClamscanProps](#cdk-serverless-clamscan-serverlessclamscanprops)</code> | A `ServerlessClamscanProps` interface.
**resultDest** | <code>[aws_lambda.IDestination](#aws-cdk-lib-aws-lambda-idestination)</code> | The Lambda Destination for completed ClamAV scans [CLEAN, INFECTED].
**scanAssumedPrincipal** | <code>[aws_iam.ArnPrincipal](#aws-cdk-lib-aws-iam-arnprincipal)</code> | <span></span>
**cleanRule**? | <code>[aws_events.Rule](#aws-cdk-lib-aws-events-rule)</code> | Conditional: An Event Bridge Rule for files that are marked 'CLEAN' by ClamAV if a success destination was not specified.<br/>__*Optional*__
**defsAccessLogsBucket**? | <code>[aws_s3.IBucket](#aws-cdk-lib-aws-s3-ibucket)</code> | Conditional: The Bucket for access logs for the virus definitions bucket if logging is enabled (defsBucketAccessLogsConfig).<br/>__*Optional*__
**errorDeadLetterQueue**? | <code>[aws_sqs.Queue](#aws-cdk-lib-aws-sqs-queue)</code> | Conditional: The SQS Dead Letter Queue for the errorQueue if a failure (onError) destination was not specified.<br/>__*Optional*__
**errorQueue**? | <code>[aws_sqs.Queue](#aws-cdk-lib-aws-sqs-queue)</code> | Conditional: The SQS Queue for erred scans if a failure (onError) destination was not specified.<br/>__*Optional*__
**infectedRule**? | <code>[aws_events.Rule](#aws-cdk-lib-aws-events-rule)</code> | Conditional: An Event Bridge Rule for files that are marked 'INFECTED' by ClamAV if a success destination was not specified.<br/>__*Optional*__
**resultBus**? | <code>[aws_events.EventBus](#aws-cdk-lib-aws-events-eventbus)</code> | Conditional: The Event Bridge Bus for completed ClamAV scans if a success (onResult) destination was not specified.<br/>__*Optional*__
**useImportedBuckets**? | <code>boolean</code> | Conditional: When true, the user accepted the responsibility for using imported buckets.<br/>__*Optional*__

### Methods


#### addSourceBucket(bucket) <a id="cdk-serverless-clamscan-serverlessclamscan-addsourcebucket"></a>

Sets the specified S3 Bucket as a s3:ObjectCreate* for the ClamAV function.

Grants the ClamAV function permissions to get and tag objects.
Adds a bucket policy to disallow GetObject operations on files that are tagged 'IN PROGRESS', 'INFECTED', or 'ERROR'.

```ts
addSourceBucket(bucket: IBucket): void
```

* **bucket** (<code>[aws_s3.IBucket](#aws-cdk-lib-aws-s3-ibucket)</code>)  The bucket to add the scanning bucket policy and s3:ObjectCreate* trigger to.




#### getPolicyStatementForBucket(bucket) <a id="cdk-serverless-clamscan-serverlessclamscan-getpolicystatementforbucket"></a>

Returns the statement that should be added to the bucket policy in order to prevent objects to be accessed when they are not clean or there have been scanning errors: this policy should be added manually if external buckets are passed to addSourceBucket().

```ts
getPolicyStatementForBucket(bucket: IBucket): PolicyStatement
```

* **bucket** (<code>[aws_s3.IBucket](#aws-cdk-lib-aws-s3-ibucket)</code>)  The bucket which you need to protect with the policy.

__Returns__:
* <code>[aws_iam.PolicyStatement](#aws-cdk-lib-aws-iam-policystatement)</code>



## struct ServerlessClamscanLoggingProps  <a id="cdk-serverless-clamscan-serverlessclamscanloggingprops"></a>


Interface for ServerlessClamscan Virus Definitions S3 Bucket Logging.



Name | Type | Description 
-----|------|-------------
**logsBucket**? | <code>boolean &#124; [aws_s3.IBucket](#aws-cdk-lib-aws-s3-ibucket)</code> | Destination bucket for the server access logs (Default: Creates a new S3 Bucket for access logs).<br/>__*Optional*__
**logsPrefix**? | <code>string</code> | Optional log file prefix to use for the bucket's access logs, option is ignored if logs_bucket is set to false.<br/>__*Optional*__



## struct ServerlessClamscanProps  <a id="cdk-serverless-clamscan-serverlessclamscanprops"></a>


Interface for creating a ServerlessClamscan.



Name | Type | Description 
-----|------|-------------
**acceptResponsibilityForUsingImportedBucket**? | <code>boolean</code> | Allows the use of imported buckets.<br/>__*Optional*__
**buckets**? | <code>Array<[aws_s3.IBucket](#aws-cdk-lib-aws-s3-ibucket)></code> | An optional list of S3 buckets to configure for ClamAV Virus Scanning;<br/>__*Optional*__
**defsBucketAccessLogsConfig**? | <code>[ServerlessClamscanLoggingProps](#cdk-serverless-clamscan-serverlessclamscanloggingprops)</code> | Whether or not to enable Access Logging for the Virus Definitions bucket, you can specify an existing bucket and prefix (Default: Creates a new S3 Bucket for access logs).<br/>__*Optional*__
**dontPreventAccessBeforeScan**? | <code>boolean</code> | When enabled the bucket policy to block access to the file before until scanning completes is not applied.<br/>__*Optional*__
**efsEncryption**? | <code>boolean</code> | Whether or not to enable encryption on EFS filesystem (Default: enabled).<br/>__*Optional*__
**efsPerformanceMode**? | <code>[aws_efs.PerformanceMode](#aws-cdk-lib-aws-efs-performancemode)</code> | Set the performance mode of the EFS file system (Default: GENERAL_PURPOSE).<br/>__*Optional*__
**onError**? | <code>[aws_lambda.IDestination](#aws-cdk-lib-aws-lambda-idestination)</code> | The Lambda Destination for files that fail to scan and are marked 'ERROR' or stuck 'IN PROGRESS' due to a Lambda timeout (Default: Creates and publishes to a new SQS queue if unspecified).<br/>__*Optional*__
**onResult**? | <code>[aws_lambda.IDestination](#aws-cdk-lib-aws-lambda-idestination)</code> | The Lambda Destination for files marked 'CLEAN' or 'INFECTED' based on the ClamAV Virus scan or 'N/A' for scans triggered by S3 folder creation events marked (Default: Creates and publishes to a new Event Bridge Bus if unspecified).<br/>__*Optional*__
**reservedConcurrency**? | <code>number</code> | Optionally set a reserved concurrency for the virus scanning Lambda.<br/>__*Optional*__
**scanFunctionMemorySize**? | <code>number</code> | Optionally set the memory allocation for the scan function.<br/>__*Optional*__



