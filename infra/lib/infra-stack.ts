import * as cdk from "aws-cdk-lib";
import { Certificate, CertificateValidation } from "aws-cdk-lib/aws-certificatemanager";
import { Vpc } from "aws-cdk-lib/aws-ec2";
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

    const image = ContainerImage.fromRegistry("amazon/amazon-ecs-sample");

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
    });

    const container = fargateTaskDefinition.addContainer("InfraContainer", {
      image,
      logging: new AwsLogDriver({ streamPrefix: id }),
    });

    container.addPortMappings({
      containerPort: 80,
    });

    const service = new FargateService(this, "InfraService", {
      cluster,
      taskDefinition: fargateTaskDefinition,
      desiredCount: 1,
      assignPublicIp: true,
    });

    targetGroup.addTarget(service);

  }
}
