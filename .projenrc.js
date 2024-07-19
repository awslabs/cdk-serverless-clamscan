const { awscdk } = require('projen');

const AUTOMATION_TOKEN = 'PROJEN_GITHUB_TOKEN';

const project = new awscdk.AwsCdkConstructLibrary({
  author: 'Amazon Web Services',
  authorAddress: 'donti@amazon.com',
  cdkVersion: '2.54.0',
  defaultReleaseBranch: 'main',
  majorVersion: 2,
  npmDistTag: 'latest',
  jsiiFqn: 'projen.AwsCdkConstructLibrary',
  name: 'cdk-serverless-clamscan',
  repositoryUrl: 'https://github.com/awslabs/cdk-serverless-clamscan',
  description: 'Serverless architecture to virus scan objects in Amazon S3.',
  devDeps: ['@aws-cdk/assert@^2.11', 'cdk-nag@^2.15.18'],
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
  license: 'Apache-2.0',
  gitignore: [
    '.vscode/',
    '.venv/',
    'cdk.out',
    'cdk.context.json',
    'dockerAssets.d',
    'package-lock.json',
    'yarn-error.log',
  ],
  pullRequestTemplateContents: [
    '',
    '----',
    '',
    '*By submitting this pull request, I confirm that my contribution is made under the terms of the Apache-2.0 license*',
  ],
  publishToPypi: {
    distName: 'cdk-serverless-clamscan',
    module: 'cdk_serverless_clamscan',
  },
  projenUpgradeSecret: AUTOMATION_TOKEN,
  autoApproveOptions: {
    secret: 'GITHUB_TOKEN',
    allowedUsernames: ['dontirun'],
  },
  autoApproveUpgrades: true,
  depsUpgradeOptions: {
    ignoreProjen: false,
    workflowOptions: {
      labels: ['auto-approve'],
      secret: AUTOMATION_TOKEN,
    },
  },
  buildWorkflow: true,
  release: true,
});
project.package.addField('resolutions', {
  'set-value': '^4.0.1',
  'ansi-regex': '^5.0.1',
  'json-schema': '^0.4.0',
  '@types/prettier': '2.6.0',
  '@types/babel__traverse': '7.18.2',
});
project.synth();
