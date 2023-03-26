from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_assets as s3_assets,
    aws_cloudformation as cloudformation,
    aws_iam as iam
)
from constructs import Construct

class DeploymentRolesStackSet(Stack):

    def __init__(self, scope: Construct, construct_id: str, account_id:str, region:str, account_names:list, org_unit_ids:list, github_oidc_role:str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cftemplate = s3_assets.Asset(self, "CloudformationTemplate",
            path="./cf_templates/terraform_deployment_roles.yaml"
        )

        # github_role = iam.Role.from_role_name(self, "github_deploy_role", role_name=github_oidc_role)

        github_oidc_role_arn = f"arn:aws:iam::{account_id}:role/{github_oidc_role}"


        cloudformation.CfnStackSet(self, "CFDeployStackSet",
            permission_model="SERVICE_MANAGED",
            stack_set_name="deploy-cloudformation-IAM-resources",
            capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            description="Stack set to deploy Terraform deploy roles in member accounts of organization.",
            auto_deployment=cloudformation.CfnStackSet.AutoDeploymentProperty(
                enabled=True,
                retain_stacks_on_account_removal=False
            ),
            managed_execution={
          "Active" : True
        },
            parameters=[cloudformation.CfnStackSet.ParameterProperty(
            parameter_key="GithubOIDCRole",
            parameter_value=github_oidc_role_arn
        )],
            stack_instances_group=[cloudformation.CfnStackSet.StackInstancesProperty(
                deployment_targets=cloudformation.CfnStackSet.DeploymentTargetsProperty(
                    account_filter_type="INTERSECTION",
                    accounts=account_names,
                    organizational_unit_ids=org_unit_ids,
                ),
                regions=[region],
            )],
            template_url=cftemplate.http_url
        )
