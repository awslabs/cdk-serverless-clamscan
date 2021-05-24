const { AwsCdkConstructLibrary } = require('projen');

const AUTOMATION_TOKEN = 'PROJEN_GITHUB_TOKEN';

const project = new AwsCdkConstructLibrary({
  author: 'Amazon Web Services',
  authorAddress: 'donti@amazon.com',
  cdkVersion: '1.101.0',
  jsiiFqn: 'projen.AwsCdkConstructLibrary',
  name: 'cdk-serverless-clamscan',
  repositoryUrl: 'https://github.com/awslabs/cdk-serverless-clamscan',


  cdkDependencies: [
    '@aws-cdk/aws-cloudtrail',
    '@aws-cdk/aws-ec2',
    '@aws-cdk/aws-efs',
    '@aws-cdk/aws-events',
    '@aws-cdk/aws-events-targets',
    '@aws-cdk/aws-iam',
    '@aws-cdk/aws-lambda',
    '@aws-cdk/aws-lambda-destinations',
    '@aws-cdk/aws-lambda-event-sources',
    '@aws-cdk/aws-s3',
    '@aws-cdk/aws-sqs',
    '@aws-cdk/core',
  ],
  cdkTestDependencies: ['@aws-cdk/assert'],
  docgen: true,
  eslint: true,
  publishToPypi: {
    distName: 'cdk-serverless-clamscan',
    module: 'cdk_serverless_clamscan',
  },

  bin: ['./assets'],
  description: 'Serverless architecture to virus scan objects in Amazon S3.',
  keywords: ['clamav', 'virus scan', 'aws', 'docker', 'serverless', 'lambda', 's3', 'efs', 'eventbridge', 'sqs'],
  license: 'Apache-2.0',
  defaultReleaseBranch: 'main',
  dependabot: false,
  projenUpgradeSecret: 'PROJEN_GITHUB_TOKEN',
  gitignore: ['.vscode/', '.venv/', 'cdk.out', 'cdk.context.json', 'dockerAssets.d', 'yarn-error.log'],
});

project.synth();
