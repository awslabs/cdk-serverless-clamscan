const { awscdk } = require('projen');

const AUTOMATION_TOKEN = 'PROJEN_GITHUB_TOKEN';
const MAJOR = 1;

const project = new awscdk.AwsCdkConstructLibrary({
  author: 'Amazon Web Services',
  authorAddress: 'donti@amazon.com',
  cdkVersion: '1.101.0',
  defaultReleaseBranch: 'main',
  majorVersion: MAJOR,
  releaseBranches: { 'v2-main': { majorVersion: 2 } },
  jsiiFqn: 'projen.AwsCdkConstructLibrary',
  name: 'cdk-serverless-clamscan',
  repositoryUrl: 'https://github.com/awslabs/cdk-serverless-clamscan',
  description: 'Serverless architecture to virus scan objects in Amazon S3.',
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
  deps: ['cdk-nag@^1.6.1'],
  devDeps: ['@aws-cdk/assert@^1'],
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
      container: {
        image: 'jsii/superchain:1-buster-slim-node14',
      },
    },
  },
  githubOptions: {
    mergify: false,
  },
  buildWorkflow: true,
  release: true,
  postBuildSteps: [
    {
      name: 'remove changelog',
      run: 'rm dist/changelog.md',
    },
    {
      name: 'Setup for monocdk build',
      run: "rm yarn.lock\nrm .projenrc.js\nmv .projenrc.monocdk.js .projenrc.js\nfind ./src -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./src -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,monocdk/assert,@monocdk-experiment/assert,g'\nfind ./src -type f | xargs sed -i  's,cdk-nag,monocdk-nag,g'\nfind ./test -type f | xargs sed -i  's,cdk-nag,monocdk-nag,g'",
    },
    {
      name: 'Bump to next version',
      run: 'npx projen bump',
    },
    {
      name: 'Build for monocdk',
      run: 'npx projen build',
    },
    {
      name: 'Unbump',
      run: 'npx projen unbump',
    },
  ],
  projenVersion: '0.45.4',
});
project.package.addField('resolutions', {
  'set-value': '^4.0.1',
  'ansi-regex': '^5.0.1',
  'json-schema': '^0.4.0',
});
const monocdkTask = project.addTask('release:monocdk', {
  env: {
    RELEASE: 'true',
    MAJOR: MAJOR,
  },
});
monocdkTask.exec('git reset --hard', { name: 'reset changes' });
monocdkTask.exec('[ -e dist/changelog.md ] && rm dist/changelog.md', {
  name: 'remove changelog',
});
monocdkTask.exec(
  "rm yarn.lock\nrm .projenrc.js\nmv .projenrc.monocdk.js .projenrc.js\nfind ./src -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./src -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,monocdk/assert,@monocdk-experiment/assert,g'\nfind ./src -type f | xargs sed -i  's,cdk-nag,monocdk-nag,g'\nfind ./test -type f | xargs sed -i  's,cdk-nag,monocdk-nag,g'",
  { name: 'Setup for monocdk build' },
);
monocdkTask.spawn('bump');
monocdkTask.spawn('build');
monocdkTask.spawn('unbump');
monocdkTask.exec('git reset --hard', { name: 'reset changes' });
const releaseWorkflow = project.tryFindObjectFile(
  '.github/workflows/release.yml',
);
releaseWorkflow.addOverride('jobs.release.env.RELEASE', 'true');
releaseWorkflow.addOverride('jobs.release.env.MAJOR', 1);
project.buildWorkflow.file.addOverride(
  'jobs.build.steps',
  project.buildWorkflow.jobs.build.steps.concat([
    {
      name: 'Setup for monocdk build',
      run: "rm yarn.lock\nrm .projenrc.js\nmv .projenrc.monocdk.js .projenrc.js\nfind ./src -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./src -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,monocdk/assert,@monocdk-experiment/assert,g'\nfind ./src -type f | xargs sed -i  's,cdk-nag,monocdk-nag,g'\nfind ./test -type f | xargs sed -i  's,cdk-nag,monocdk-nag,g'",
    },
    {
      name: 'Build for monocdk',
      run: 'npx projen build',
    },
  ]),
);
project.synth();
