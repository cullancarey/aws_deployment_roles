from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_cloudtrail as cloudtrail
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct


class OrganizationAuditResourcesStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cloudtrail_trail_name: str,
        cloudtrail_logs_bucket_name: str,
        athena_query_results_bucket_name: str,
        organization_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cloudtrail_logs_bucket = s3.Bucket(
            self,
            "CloudTrailLogsBucket",
            bucket_name=cloudtrail_logs_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
        )

        athena_query_results_bucket = s3.Bucket(
            self,
            "AthenaQueryResultsBucket",
            bucket_name=athena_query_results_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
        )

        cloudtrail_trail = cloudtrail.CfnTrail(
            self,
            "OrganizationTrail",
            trail_name=cloudtrail_trail_name,
            s3_bucket_name=cloudtrail_logs_bucket.bucket_name,
            include_global_service_events=True,
            is_multi_region_trail=True,
            enable_log_file_validation=True,
            is_organization_trail=True,
            is_logging=True,
        )

        trail_arn = f"arn:aws:cloudtrail:{self.region}:{self.account}:trail/{cloudtrail_trail_name}"

        cloudtrail_logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AWSCloudTrailAclCheck",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=["s3:GetBucketAcl"],
                resources=[cloudtrail_logs_bucket.bucket_arn],
                conditions={"StringEquals": {"AWS:SourceArn": trail_arn}},
            )
        )

        cloudtrail_logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AWSCloudTrailWriteOrg",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=["s3:PutObject"],
                resources=[
                    f"{cloudtrail_logs_bucket.bucket_arn}/AWSLogs/{organization_id}/*"
                ],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": trail_arn,
                        "s3:x-amz-acl": "bucket-owner-full-control",
                    }
                },
            )
        )

        cloudtrail_logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AWSCloudTrailWriteAccount",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=["s3:PutObject"],
                resources=[
                    f"{cloudtrail_logs_bucket.bucket_arn}/AWSLogs/{self.account}/*"
                ],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": trail_arn,
                        "s3:x-amz-acl": "bucket-owner-full-control",
                    }
                },
            )
        )

        CfnOutput(
            self,
            "CloudTrailTrailName",
            value=cloudtrail_trail_name,
        )
        CfnOutput(
            self,
            "CloudTrailLogsBucketName",
            value=cloudtrail_logs_bucket.bucket_name,
        )
        CfnOutput(
            self,
            "AthenaQueryResultsBucketName",
            value=athena_query_results_bucket.bucket_name,
        )
