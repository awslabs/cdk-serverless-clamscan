# API Reference

**Classes**

Name|Description
----|-----------
[ServerlessClamscan](#cdk-serverless-clamscan-serverlessclamscan)|An [aws-cdk](https://github.com/aws/aws-cdk) construct that uses [ClamAV®](https://www.clamav.net/). to scan objects in Amazon S3 for viruses. The construct provides a flexible interface for a system to act based on the results of a ClamAV virus scan.  The construct creates a Lambda function with EFS integration to support larger files. A VPC with isolated subnets, a S3 Gateway endpoint will also be created.  Additionally creates an twice-daily job to download the latest ClamAV definition files to the Virus Definitions S3 Bucket by utilizing an EventBridge rule and a Lambda function and publishes CloudWatch Metrics to the 'serverless-clamscan' namespace.  __Important O&M__: When ClamAV publishes updates to the scanner you will see “Your ClamAV installation is OUTDATED” in your scan results. While the construct creates a system to keep the database definitions up to date, you must update the scanner to detect all the latest Viruses.  Update the docker images of the Lambda functions with the latest version of ClamAV by re-running `cdk deploy`.  Successful Scan Event format ```json {     "source": "serverless-clamscan",     "input_bucket": <input_bucket_name>,     "input_key": <object_key>,     "status": <"CLEAN"|"INFECTED"|"N/A">,     "message": <scan_summary>,   } ```  Note: The Virus Definitions bucket policy will likely cause a deletion error if you choose to delete the stack associated in the construct. However since the bucket itself gets deleted, you can delete the stack again to resolve the error.


**Structs**

Name|Description
----|-----------
[ServerlessClamscanLoggingProps](#cdk-serverless-clamscan-serverlessclamscanloggingprops)|Interface for ServerlessClamscan Virus Definitions S3 Bucket Logging.
[ServerlessClamscanProps](#cdk-serverless-clamscan-serverlessclamscanprops)|Interface for creating a ServerlessClamscan.



## class ServerlessClamscan  <a id="cdk-serverless-clamscan-serverlessclamscan"></a>

An [aws-cdk](https://github.com/aws/aws-cdk) construct that uses [ClamAV®](https://www.clamav.net/). to scan objects in Amazon S3 for viruses. The construct provides a flexible interface for a system to act based on the results of a ClamAV virus scan.  The construct creates a Lambda function with EFS integration to support larger files. A VPC with isolated subnets, a S3 Gateway endpoint will also be created.  Additionally creates an twice-daily job to download the latest ClamAV definition files to the Virus Definitions S3 Bucket by utilizing an EventBridge rule and a Lambda function and publishes CloudWatch Metrics to the 'serverless-clamscan' namespace.  __Important O&M__: When ClamAV publishes updates to the scanner you will see “Your ClamAV installation is OUTDATED” in your scan results. While the construct creates a system to keep the database definitions up to date, you must update the scanner to detect all the latest Viruses.  Update the docker images of the Lambda functions with the latest version of ClamAV by re-running `cdk deploy`.  Successful Scan Event format ```json {     "source": "serverless-clamscan",     "input_bucket": <input_bucket_name>,     "input_key": <object_key>,     "status": <"CLEAN"|"INFECTED"|"N/A">,     "message": <scan_summary>,   } ```  Note: The Virus Definitions bucket policy will likely cause a deletion error if you choose to delete the stack associated in the construct. However since the bucket itself gets deleted, you can delete the stack again to resolve the error.

__Implements__: [IConstruct](#constructs-iconstruct), [IConstruct](#aws-cdk-core-iconstruct), [IConstruct](#constructs-iconstruct), [IDependable](#aws-cdk-core-idependable)
__Extends__: [Construct](#aws-cdk-core-construct)

### Initializer


Creates a ServerlessClamscan construct.

```ts
new ServerlessClamscan(scope: Construct, id: string, props: ServerlessClamscanProps)
```

* **scope** (<code>[Construct](#aws-cdk-core-construct)</code>)  The parent creating construct (usually `this`).
* **id** (<code>string</code>)  The construct's name.
* **props** (<code>[ServerlessClamscanProps](#cdk-serverless-clamscan-serverlessclamscanprops)</code>)  A `ServerlessClamscanProps` interface.
  * **buckets** (<code>Array<[Bucket](#aws-cdk-aws-s3-bucket)></code>)  An optional list of S3 buckets to configure for ClamAV Virus Scanning; __*Optional*__
  * **defsBucketAccessLogsConfig** (<code>[ServerlessClamscanLoggingProps](#cdk-serverless-clamscan-serverlessclamscanloggingprops)</code>)  Whether or not to enable Access Logging for the Virus Definitions bucket, you can specify an existing bucket and prefix (Default: Creates a new S3 Bucket for access logs ). __*Optional*__
  * **efsEncryption** (<code>boolean</code>)  Whether or not to enable encryption on EFS filesystem (Default: enabled). __*Optional*__
  * **onError** (<code>[IDestination](#aws-cdk-aws-lambda-idestination)</code>)  The Lambda Destination for files that fail to scan and are marked 'ERROR' or stuck 'IN PROGRESS' due to a Lambda timeout (Default: Creates and publishes to a new SQS queue if unspecified). __*Optional*__
  * **onResult** (<code>[IDestination](#aws-cdk-aws-lambda-idestination)</code>)  The Lambda Destination for files marked 'CLEAN' or 'INFECTED' based on the ClamAV Virus scan or 'N/A' for scans triggered by S3 folder creation events marked (Default: Creates and publishes to a new Event Bridge Bus if unspecified). __*Optional*__
  * **vpc** (<code>[IVpc](#aws-cdk-aws-ec2-ivpc)</code>)  You can specify an existing VPC (Default: Creates a VPC with isolated subnets). __*Optional*__



### Properties


Name | Type | Description 
-----|------|-------------
**errorDest** | <code>[IDestination](#aws-cdk-aws-lambda-idestination)</code> | The Lambda Destination for failed on erred scans [ERROR, IN PROGRESS (If error is due to Lambda timeout)].
**resultDest** | <code>[IDestination](#aws-cdk-aws-lambda-idestination)</code> | The Lambda Destination for completed ClamAV scans [CLEAN, INFECTED].
**cleanRule**? | <code>[Rule](#aws-cdk-aws-events-rule)</code> | Conditional: An Event Bridge Rule for files that are marked 'CLEAN' by ClamAV if a success destination was not specified.<br/>__*Optional*__
**defsAccessLogsBucket**? | <code>[Bucket](#aws-cdk-aws-s3-bucket)</code> | Conditional: The Bucket for access logs for the virus definitions bucket if logging is enabled (defsBucketAccessLogsConfig).<br/>__*Optional*__
**errorDeadLetterQueue**? | <code>[Queue](#aws-cdk-aws-sqs-queue)</code> | Conditional: The SQS Dead Letter Queue for the errorQueue if a failure (onError) destination was not specified.<br/>__*Optional*__
**errorQueue**? | <code>[Queue](#aws-cdk-aws-sqs-queue)</code> | Conditional: The SQS Queue for erred scans if a failure (onError) destination was not specified.<br/>__*Optional*__
**infectedRule**? | <code>[Rule](#aws-cdk-aws-events-rule)</code> | Conditional: An Event Bridge Rule for files that are marked 'INFECTED' by ClamAV if a success destination was not specified.<br/>__*Optional*__
**resultBus**? | <code>[EventBus](#aws-cdk-aws-events-eventbus)</code> | Conditional: The Event Bridge Bus for completed ClamAV scans if a success (onResult) destination was not specified.<br/>__*Optional*__

### Methods


#### addSourceBucket(bucket) <a id="cdk-serverless-clamscan-serverlessclamscan-addsourcebucket"></a>

Sets the specified S3 Bucket as a s3:ObjectCreate* for the ClamAV function.

Grants the ClamAV function permissions to get and tag objects.
Adds a bucket policy to disallow GetObject operations on files that are tagged 'IN PROGRESS', 'INFECTED', or 'ERROR'.

```ts
addSourceBucket(bucket: Bucket): void
```

* **bucket** (<code>[Bucket](#aws-cdk-aws-s3-bucket)</code>)  The bucket to add the scanning bucket policy and s3:ObjectCreate* trigger to.






## struct ServerlessClamscanLoggingProps  <a id="cdk-serverless-clamscan-serverlessclamscanloggingprops"></a>


Interface for ServerlessClamscan Virus Definitions S3 Bucket Logging.



Name | Type | Description 
-----|------|-------------
**logsBucket**? | <code>boolean &#124; [Bucket](#aws-cdk-aws-s3-bucket)</code> | Destination bucket for the server access logs (Default: Creates a new S3 Bucket for access logs ).<br/>__*Optional*__
**logsPrefix**? | <code>string</code> | Optional log file prefix to use for the bucket's access logs, option is ignored if logs_bucket is set to false.<br/>__*Optional*__



## struct ServerlessClamscanProps  <a id="cdk-serverless-clamscan-serverlessclamscanprops"></a>


Interface for creating a ServerlessClamscan.



Name | Type | Description 
-----|------|-------------
**buckets**? | <code>Array<[Bucket](#aws-cdk-aws-s3-bucket)></code> | An optional list of S3 buckets to configure for ClamAV Virus Scanning;<br/>__*Optional*__
**defsBucketAccessLogsConfig**? | <code>[ServerlessClamscanLoggingProps](#cdk-serverless-clamscan-serverlessclamscanloggingprops)</code> | Whether or not to enable Access Logging for the Virus Definitions bucket, you can specify an existing bucket and prefix (Default: Creates a new S3 Bucket for access logs ).<br/>__*Optional*__
**efsEncryption**? | <code>boolean</code> | Whether or not to enable encryption on EFS filesystem (Default: enabled).<br/>__*Optional*__
**onError**? | <code>[IDestination](#aws-cdk-aws-lambda-idestination)</code> | The Lambda Destination for files that fail to scan and are marked 'ERROR' or stuck 'IN PROGRESS' due to a Lambda timeout (Default: Creates and publishes to a new SQS queue if unspecified).<br/>__*Optional*__
**onResult**? | <code>[IDestination](#aws-cdk-aws-lambda-idestination)</code> | The Lambda Destination for files marked 'CLEAN' or 'INFECTED' based on the ClamAV Virus scan or 'N/A' for scans triggered by S3 folder creation events marked (Default: Creates and publishes to a new Event Bridge Bus if unspecified).<br/>__*Optional*__
**vpc**? | <code>[IVpc](#aws-cdk-aws-ec2-ivpc)</code> | You can specify an existing VPC (Default: Creates a VPC with isolated subnets).<br/>__*Optional*__



