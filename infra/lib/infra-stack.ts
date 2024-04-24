import * as cdk from "aws-cdk-lib";
import { Certificate, CertificateValidation } from "aws-cdk-lib/aws-certificatemanager";
import { BuildSpec, EventAction, FilterGroup, GitHubSourceCredentials, LinuxBuildImage, Project, Source } from "aws-cdk-lib/aws-codebuild";
import { Artifact, ArtifactPath, Pipeline, PipelineType } from "aws-cdk-lib/aws-codepipeline";
import { CodeBuildAction, CodeStarConnectionsSourceAction, EcsDeployAction, GitHubSourceAction, ManualApprovalAction } from "aws-cdk-lib/aws-codepipeline-actions";
import { Vpc } from "aws-cdk-lib/aws-ec2";
import { Repository } from "aws-cdk-lib/aws-ecr";
import {
  AwsLogDriver,
  Cluster,
  ContainerImage,
  FargateService,
  FargateTaskDefinition,
} from "aws-cdk-lib/aws-ecs";
import {
  ApplicationLoadBalancer,
  ApplicationProtocol,
  ListenerAction,
  ListenerCertificate,
  SslPolicy,
} from "aws-cdk-lib/aws-elasticloadbalancingv2";
import { Effect, ManagedPolicy, PolicyStatement, Role, ServicePrincipal } from "aws-cdk-lib/aws-iam";
import { ARecord, CnameRecord, HostedZone, RecordTarget } from "aws-cdk-lib/aws-route53";
import { LoadBalancerTarget } from "aws-cdk-lib/aws-route53-targets";
import { Construct } from "constructs";

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    
    const domainName = "oxfarmtofork.org";

    const vpc = new Vpc(this, "InfraVpc", {
      maxAzs: 2,
    })

    const cluster = new Cluster(this, "InfraCluster", {
      vpc: vpc,
      clusterName: "InfraCluster",
      containerInsights: true,
    });

    const repo = Repository.fromRepositoryName(this, "InfraRepository", "infra-repository");
    const image = ContainerImage.fromEcrRepository(repo, "latest");

    const taskRole = new Role(this, 'Streamlit Execution Role', {
      assumedBy: new ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    const lambdaInvokePolicy = new PolicyStatement({
      effect: Effect.ALLOW,
      actions: ['lambda:InvokeFunction'],
      resources: ['*'], // You can specify specific Lambda function ARNs here for better security
    });

    taskRole.addToPolicy(lambdaInvokePolicy);
    taskRole.addManagedPolicy(ManagedPolicy.fromAwsManagedPolicyName('AmazonS3FullAccess'));

    const loadBalancer = new ApplicationLoadBalancer(this, "InfraLoadBalancer", {
      vpc: vpc,
      internetFacing: true,
      idleTimeout: cdk.Duration.seconds(120),
    });

    const hostedZone = HostedZone.fromLookup(this, "InfraHostedZone", {
      domainName,
    });

    const certificate = new Certificate(this, "InfraCertificate", {
      domainName,
      validation: CertificateValidation.fromDns(hostedZone),
    });

    const listener = loadBalancer.addListener("InfraListener", {
      protocol: ApplicationProtocol.HTTPS,
      sslPolicy: SslPolicy.RECOMMENDED,
    })

    const targetGroup = listener.addTargets("InfraTargetGroup", {
      protocol: ApplicationProtocol.HTTP,
    });

    listener.addCertificates("InfraCertificate", [ListenerCertificate.fromCertificateManager(certificate)]);

    loadBalancer.addListener('PublicRedirectListener', {
      protocol: ApplicationProtocol.HTTP,
      port: 80,
      open: true,
      defaultAction: ListenerAction.redirect({
        port: '443',
        protocol: ApplicationProtocol.HTTPS,
        permanent: true,
      }),
    });
    
    new ARecord(this, "InfraCnameRecord", {
      zone: hostedZone,
      recordName: domainName,
      target: RecordTarget.fromAlias(new LoadBalancerTarget(loadBalancer))
    });

    new cdk.CfnOutput(this, "InfraLoadBalancerDNS", { value: loadBalancer.loadBalancerDnsName });
    new cdk.CfnOutput(this, "ServiceURL", { value: "https://" +  domainName});

    const fargateTaskDefinition = new FargateTaskDefinition(this, "InfraTaskDefinition", {
      memoryLimitMiB: 2048,
      cpu: 1024,
      taskRole
    });

    const container = fargateTaskDefinition.addContainer("InfraContainer", {
      image,
      logging: new AwsLogDriver({ streamPrefix: id }),
    });

    container.addPortMappings({
      containerPort: 8501,
    });

    const service = new FargateService(this, "InfraService", {
      cluster,
      taskDefinition: fargateTaskDefinition,
      desiredCount: 1,
      assignPublicIp: true,
    });

    targetGroup.addTarget(service);

    const githubUserName = "dougbrierley"
    const githubRepository = "F2F"

    const gitHubSource = Source.gitHub({
      owner: githubUserName,
      repo: githubRepository,
    });

    const project = new Project(this, 'Streamlit Farm to Fork', {
      projectName: `${this.stackName}`,
      source: gitHubSource,
      environment: {
        buildImage: LinuxBuildImage.AMAZON_LINUX_2_5,
        privileged: true
      },
      environmentVariables: {
        'cluster_name': {
          value: `${cluster.clusterName}`
        },
        'ecr_repo_uri': {
          value: `${repo.repositoryUri}`
        },
        'AWS_ACCOUNT_ID': {
          value: `${this.account}`
        },
        'AWS_DEFAULT_REGION': {
          value: `${this.region}`
        }
      },
      badge: true,
      buildSpec: BuildSpec.fromObject({
        version: "0.2",
        phases: {
          pre_build: {
            commands: [
              'env',
              'export tag=latest'
            ]
          },
          build: {
            commands: [
              'cd streamlit',
              `docker build -t $ecr_repo_uri:$tag .`,
              `aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com`,
              'docker push $ecr_repo_uri:$tag'
            ]
          },
          post_build: {
            commands: [
              'echo "in post-build stage"',
              'cd ..',
              "printf '[{\"name\":\"" + container.containerName + "\",\"imageUri\":\"%s\"}]' $ecr_repo_uri:$tag > imagedefinitions.json",
              "pwd; ls -al; cat imagedefinitions.json"
            ]
          }
        },
        artifacts: {
          files: [
            'imagedefinitions.json'
          ]
        }
      })
    });

    const sourceOutput = new Artifact();
    const buildOutput = new Artifact();
    const sourceAction = new CodeStarConnectionsSourceAction({
      actionName: 'github_source',
      owner: githubUserName,
      repo: githubRepository,
      branch: 'main',
      connectionArn: 'arn:aws:codestar-connections:eu-west-2:850434255294:connection/1d9da8cd-514b-4630-945f-ce20a7a7cece',
      output: sourceOutput,
      triggerOnPush: true,
    });

    const buildAction = new CodeBuildAction({
      actionName: 'codebuild',
      project: project,
      input: sourceOutput,
      outputs: [buildOutput],
    });

    // const manualApprovalAction = new ManualApprovalAction({
    //   actionName: 'approve',
    // });

    const deployAction = new EcsDeployAction({
      actionName: 'deployAction',
      service,
      imageFile: new ArtifactPath(buildOutput, `imagedefinitions.json`)
    });

    new Pipeline(this, 'StreamlitFarmToForkPipeline', {
      pipelineType: PipelineType.V2,
      stages: [
        {
          stageName: 'source',
          actions: [sourceAction],
        },
        {
          stageName: 'build',
          actions: [buildAction],
        },
        // {
        //   stageName: 'approve',
        //   actions: [manualApprovalAction],
        // },
        {
          stageName: 'deploy-to-ecs',
          actions: [deployAction],
        }
      ]
    });

    repo.grantPullPush(project);
    project.addToRolePolicy(new PolicyStatement({
      actions: [
        "ecs:describecluster",
        "ecr:getauthorizationtoken",
        "ecr:batchchecklayeravailability",
        "ecr:batchgetimage",
        "ecr:getdownloadurlforlayer"
      ],
      resources: [`${cluster.clusterArn}`],
    }));


  }
}
