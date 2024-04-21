import * as cdk from "aws-cdk-lib";
import { Port, SubnetType, Vpc } from "aws-cdk-lib/aws-ec2";
import { Repository } from "aws-cdk-lib/aws-ecr";
import { Cluster, EcrImage, FargateService, FargateTaskDefinition } from "aws-cdk-lib/aws-ecs";
import { ApplicationLoadBalancer } from "aws-cdk-lib/aws-elasticloadbalancingv2";
import { ARecord, HostedZone, RecordTarget } from "aws-cdk-lib/aws-route53";
import { LoadBalancerTarget } from "aws-cdk-lib/aws-route53-targets";
import { Construct } from "constructs";

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const vpc = new Vpc(this, "InfraVpc", { maxAzs: 2 });

    const cluster = new Cluster(this, "Ec2Cluster", { vpc });

    const repo = new Repository(this, "farmtoforkstreamlitrepo");
    const image = new EcrImage(repo, "farmtoforkstreamlitapp");

    const taskDefinition = new FargateTaskDefinition(this, "StreamlitTaskDefinition");
    taskDefinition.addContainer("streamlitcontainer", {
      image: image,
      portMappings: [{ containerPort: 8080 }]
    })

    const hostedZone = HostedZone.fromLookup(this, 'oxfarmtofork.org', {
      domainName: 'oxfarmtofork.org'
    });

    const loadBalancer = new ApplicationLoadBalancer(this, "LoadBalancer", {
      vpc,
      internetFacing: true,
    });

    const albAlias = new LoadBalancerTarget(loadBalancer);
    new ARecord(this, 'ARecord', {
        zone: hostedZone,
        target: RecordTarget.fromAlias(albAlias),
    });

    const service = new FargateService(this, "StreamlitService", {
      cluster,
      taskDefinition,
      desiredCount: 1,
      vpcSubnets: {
        subnetType: SubnetType.PUBLIC
      },
    });

    service.connections.allowFrom(
      loadBalancer,
      Port.tcp(8080),
      "Allow inbound traffic from ALB"
    )

    const Listener = loadBalancer.addListener("Listener", {
      port: 80,
      open: true,
    });


    Listener.addTargets("ECS", {
      port: 8080,
      targets: [service],
    });
  }
}
