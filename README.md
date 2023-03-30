# aws_deployment_roles
This repo holds CDK code which creates a Cloudformation stackset to deploy the terraform deployment roles used for my websites deployment. View more information about my website in the [website](https://github.com/cullancarey/website) repository. 

## Architecture
The below image outlines the architecture design for this stackset and the deployment of the website utilizing the deployment roles. This model utiilizes a centralized deployment architecture. 

![image](./website_automation_arch.png)

## CDK StackSet
This is a Python code (seen [here](./cdk/cdk/deployment_role_stack_set.py) using the AWS Cloud Development Kit (CDK) to create an AWS CloudFormation StackSet for deploying Terraform deploy roles in member accounts of an organization.

The code defines a class DeploymentRolesStackSet that extends the AWS CDK Stack class. This class has a constructor method that initializes the stack. The constructor takes in several parameters such as scope, construct_id, account_id, region, account_names, org_unit_ids, and github_oidc_role.

The cftemplate variable is an AWS S3 asset that represents the CloudFormation template that will be deployed using the StackSet. The repos variable hold repo names that are allowed to assume the GitHub OIDC role.

The cloudformation.CfnStackSet method is used to create the StackSet. The permission_model parameter is set to "SERVICE_MANAGED" which means AWS CloudFormation creates and manages the necessary AWS Identity and Access Management (IAM) resources. The stack_set_name parameter is set to "deploy-cloudformation-IAM-resources". The capabilities parameter specifies the capabilities required to create and update the StackSet.

The description parameter provides a description of the StackSet. The auto_deployment parameter specifies the configuration for automatically deploying the StackSet. The managed_execution parameter specifies that the execution is managed. The parameters parameter is used to specify the SubjectClaimFilters parameter that is passed to the CloudFormation template. The stack_instances_group parameter specifies the target accounts and regions for deploying the StackSet.

Finally, the template_url parameter is used to specify the URL of the CloudFormation template that is used to create the StackSet.

## Deployment Roles Cloudformation Template
This is an AWS CloudFormation template that creates an OIDC provider and a role for use with GitHub Actions.

The Parameters section allows the user to specify comma-separated lists of thumbprints, allowed audiences, and subject claim filters for valid tokens. The Resources section then creates an AWS::IAM::OIDCProvider and an AWS::IAM::Role.

The AWS::IAM::OIDCProvider resource creates an OIDC provider in IAM, which represents the identity provider that is used to authenticate users for AWS API calls. The Url property specifies the endpoint for the GitHub Actions token service. The ThumbprintList and ClientIdList properties are set to the parameters defined in the Parameters section.

The AWS::IAM::Role resource creates a role that allows GitHub Actions to assume the role using the OIDC provider. The RoleName property is set to a unique identifier for the role, while the AssumeRolePolicyDocument property specifies the conditions under which the role can be assumed. The Policies property defines the policies that are attached to the role, which in this case is a policy that allows all actions on all resources. I plan to refine these permissions in the near future.

Overall, this CloudFormation template sets up an authentication mechanism that allows GitHub Actions to perform actions on AWS resources using the IAM role defined in the template.