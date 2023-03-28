#!/usr/bin/env python3
"""Module import for cdk and other required packages"""
import os
from aws_cdk import App, Tags, Environment
from cdk.deployment_role_stack_set import DeploymentRolesStackSet


app = App()

print(os.environ.get("ENVIRONMENT"))

github_oidc_role = os.environ.get("GITHUBDEPLOYROLE")
account = os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"])
region = os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
account_names = ["693590665244", "045107234435", "651295191577"]
org_unit_ids = ["ou-u85y-akfavhg4", "ou-u85y-sfao42dv"]

default_tags = {
    "stack_name": "DeploymentRolesStackSet",
}

env = Environment(
    account=account,
    region=region)


for key, value in default_tags.items():
    Tags.of(app).add(key, value)

DeploymentRolesStackSet(
    app,
    construct_id="DeploymentRolesStackSet",
    account_id=account,
    region=region,
    account_names=account_names,
    org_unit_ids=org_unit_ids,
    github_oidc_role=github_oidc_role,
    description=f"Stackset used for deploying Terraform deployment roles to memeber accounts",
    env=env
)

app.synth()
