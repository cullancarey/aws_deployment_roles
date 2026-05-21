#!/usr/bin/env python3
"""Module import for cdk and other required packages"""
import os
from aws_cdk import App, Tags, Environment
from cdk.deployment_role_stack_set import DeploymentRolesStackSet
from cdk.organization_audit_resources_stack import OrganizationAuditResourcesStack


app = App()

# Get environment from env var or context, default to "management"
environment = (
    os.environ.get("ENVIRONMENT")
    or app.node.try_get_context("environment")
    or "management"
)
print(f"Environment: {environment}")

environment_config = app.node.try_get_context(environment)

account = environment_config.get("account_id")
region = environment_config.get("region")

# Deployment role stack configuration
github_oidc_role = os.environ.get("GITHUBDEPLOYROLE")
stack_set_account_ids = environment_config.get("stack_set_account_ids", "").split(",")
stack_set_org_unit_ids = environment_config.get("stack_set_org_unit_ids", "").split(",")

default_tags = {
    "stack_name": "DeploymentRolesStackSet",
}

env = Environment(account=account, region=region)

for key, value in default_tags.items():
    Tags.of(app).add(key, value)

DeploymentRolesStackSet(
    app,
    construct_id="DeploymentRolesStackSet",
    account_id=account,
    region=region,
    account_ids=stack_set_account_ids,
    org_unit_ids=stack_set_org_unit_ids,
    description=f"Stackset used for deploying Terraform deployment roles to memeber accounts",
    env=env,
)

# Organization audit resources configuration
org_audit_config = environment_config.get("organization_audit")

cloudtrail_trail_name = org_audit_config.get("cloudtrail_trail_name")
cloudtrail_logs_bucket_name = org_audit_config.get("cloudtrail_logs_bucket_name")
athena_query_results_bucket_name = org_audit_config.get(
    "athena_query_results_bucket_name"
)
organization_id = org_audit_config.get("organization_id")

OrganizationAuditResourcesStack(
    app,
    construct_id="OrganizationAuditResourcesStack",
    cloudtrail_trail_name=cloudtrail_trail_name,
    cloudtrail_logs_bucket_name=cloudtrail_logs_bucket_name,
    athena_query_results_bucket_name=athena_query_results_bucket_name,
    organization_id=organization_id,
    env=env,
)

app.synth()
