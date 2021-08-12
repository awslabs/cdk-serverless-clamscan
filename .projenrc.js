const {
  AwsCdkConstructLibrary,
  DependenciesUpgradeMechanism,
} = require('projen');

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
  bin: ['./assets'],
  description: 'Serverless architecture to virus scan objects in Amazon S3.',
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
  defaultReleaseBranch: 'main',
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
  depsUpgrade: DependenciesUpgradeMechanism.githubWorkflow({
    ignoreProjen: false,
    workflowOptions: {
      labels: ['auto-approve'],
      secret: AUTOMATION_TOKEN,
      container: {
        image: 'jsii/superchain',
      },
    },
  }),
  buildWorkflow: true,
  release: true,
});

project.package.addField('resolutions', {
  'trim-newlines': '3.0.1',
});
project.buildWorkflow.file.addOverride('jobs.build.steps', [
  {
    name: 'Checkout',
    uses: 'actions/checkout@v2',
    with: {
      ref: '${{ github.event.pull_request.head.ref }}',
      repository: '${{ github.event.pull_request.head.repo.full_name }}',
    },
  },
  {
    name: 'Install dependencies',
    run: 'yarn install --check-files --frozen-lockfile',
  },
  {
    name: 'Set git identity',
    run: 'git config user.name "Automation"\ngit config user.email "github-actions@github.com"',
  },
  {
    name: 'Build for cdk',
    run: 'npx projen build',
  },
  {
    name: 'Check for changes',
    id: 'git_diff',
    run: 'git diff --exit-code || echo "::set-output name=has_changes::true"',
  },
  {
    if: 'steps.git_diff.outputs.has_changes',
    name: 'Commit and push changes (if changed)',
    run: 'git add . && git commit -m "chore: self mutation" \n&& git push origin HEAD:${{ github.event.pull_request.head.ref }}',
  },
  {
    if: 'steps.git_diff.outputs.has_changes',
    name: 'Update status check (if changed)',
    run: 'gh api -X POST /repos/${{ github.event.pull_request.head.repo.full_name }}/check-runs -F name="build" -F head_sha="$(git rev-parse HEAD)" -F status="completed" -F conclusion="success"',
    env: {
      GITHUB_TOKEN: '${{ secrets.GITHUB_TOKEN }}',
    },
  },
  {
    if: 'steps.git_diff.outputs.has_changes',
    name: 'Cancel workflow (if changed)',
    run: 'gh api -X POST /repos/${{ github.event.pull_request.head.repo.full_name }}/actions/runs/${{ github.run_id }}/cancel',
    env: {
      GITHUB_TOKEN: '${{ secrets.GITHUB_TOKEN }}',
    },
  },
  {
    name: 'Setup for monocdk build',
    run: "rm yarn.lock\nrm .projenrc.js\nmv .projenrc.monocdk.js .projenrc.js\nfind ./src -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./src -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,monocdk/assert,@monocdk-experiment/assert,g'",
  },
  {
    name: 'Build for monocdk',
    run: 'npx projen build',
    env: {
      GITHUB_TOKEN: '${{ secrets.GITHUB_TOKEN }}',
    },
  },
]);
project.release.addJobs({
  release: {
    runsOn: 'ubuntu-latest',
    permissions: {
      contents: 'write',
    },
    outputs: {
      latest_commit: '${{ steps.git_remote.outputs.latest_commit }}',
    },
    env: {
      CI: 'true',
    },
    steps: [
      {
        name: 'Checkout',
        uses: 'actions/checkout@v2',
        with: {
          'fetch-depth': 0,
        },
      },
      {
        name: 'Set git identity',
        run: 'git config user.name "Automation"\ngit config user.email "github-actions@github.com"',
      },
      {
        name: 'Install dependencies',
        run: 'yarn install --check-files --frozen-lockfile',
      },
      {
        name: 'Bump to next version',
        run: 'npx projen bump',
      },
      {
        name: 'build',
        run: 'npx projen build',
      },
      {
        name: 'Backup version file',
        run: 'cp -f package.json package.json.bak.json',
      },
      {
        name: 'remove changelog',
        run: 'rm dist/changelog.md',
      },
      {
        name: 'Unbump',
        run: 'npx projen unbump',
      },
      {
        name: 'Anti-tamper check',
        run: 'git diff --ignore-space-at-eol --exit-code',
      },
      {
        name: 'Setup for monocdk build',
        run: "rm yarn.lock\nrm .projenrc.js\nmv .projenrc.monocdk.js .projenrc.js\nfind ./src -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk/core,monocdk,g'\nfind ./src -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,@aws-cdk,monocdk,g'\nfind ./test -type f | xargs sed -i  's,monocdk/assert,@monocdk-experiment/assert,g'",
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
        name: 'Backup version file',
        run: 'cp -f package.json package.json.bak.json',
      },
      {
        name: 'Unbump',
        run: 'npx projen unbump',
      },
      {
        name: 'Check for new commits',
        id: 'git_remote',
        run: 'echo ::set-output name=latest_commit::"$(git ls-remote origin -h ${{ github.ref }} | cut -f1)"',
      },
      {
        name: 'Create release',
        if: '${{ steps.git_remote.outputs.latest_commit == github.sha }}',
        run: 'gh release create v$(node -p "require(\'./package.json.bak.json\').version") -F dist/changelog.md -t v$(node -p "require(\'./package.json.bak.json\').version")',
        env: {
          GITHUB_TOKEN: '${{ secrets.GITHUB_TOKEN }}',
        },
      },
      {
        name: 'Upload artifact',
        if: '${{ steps.git_remote.outputs.latest_commit == github.sha }}',
        uses: 'actions/upload-artifact@v2.1.1',
        with: {
          name: 'dist',
          path: 'dist',
        },
      },
    ],
    container: {
      image: 'jsii/superchain',
    },
  },
});

project.synth();
