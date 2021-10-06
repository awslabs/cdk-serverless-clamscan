const { AwsCdkConstructLibrary } = require('projen');

const AUTOMATION_TOKEN = 'PROJEN_GITHUB_TOKEN';

const project = new AwsCdkConstructLibrary({
  author: 'Amazon Web Services',
  authorAddress: 'donti@amazon.com',
  cdkVersion: '1.101.0',
  jsiiFqn: 'projen.AwsCdkConstructLibrary',
  name: 'monocdk-serverless-clamscan',
  description: 'Serverless architecture to virus scan objects in Amazon S3.',
  repositoryUrl: 'https://github.com/awslabs/cdk-serverless-clamscan',

  cdkDependencies: ['monocdk'],
  cdkTestDependencies: ['@monocdk-experiment/assert'],
  devDeps: ['monocdk-nag'],
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
