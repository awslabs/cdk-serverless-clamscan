const { awscdk } = require('projen');

const project = new awscdk.AwsCdkConstructLibrary({
  author: 'Amazon Web Services',
  authorAddress: 'donti@amazon.com',
  cdkVersion: '1.101.0',
  defaultReleaseBranch: 'main',
  jsiiFqn: 'projen.AwsCdkConstructLibrary',
  name: 'monocdk-serverless-clamscan',
  description: 'Serverless architecture to virus scan objects in Amazon S3.',
  repositoryUrl: 'https://github.com/awslabs/cdk-serverless-clamscan',
  cdkDependencies: ['monocdk'],
  cdkTestDependencies: ['@monocdk-experiment/assert'],
  deps: ['monocdk-nag@^1.6.1'],
  publishToPypi: {
    distName: 'monocdk-serverless-clamscan',
    module: 'monocdk_serverless_clamscan',
  },

  bin: ['./assets'],
  keywords: [
    'clamav',
    'virus scan',
    'aws',
    'docker',
    'serverless',
    'lambda',
    's3',
    'efs',
    'eventbridge',
    'sqs',
  ],
});

project.synth();
