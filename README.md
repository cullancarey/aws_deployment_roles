# aws_deployment_roles
This repo holds CloudFormation templates and CDK code for creating GitHub Actions OIDC deployment roles. The roles have been refactored from a single overprivileged role to two specialized roles: one for Terraform deployments and one for CDK deployments, following the principle of least privilege.

View more information about my website deployment in the [website](https://github.com/cullancarey/website) repository. 

## Architecture
The below image outlines the architecture design for this stackset and the deployment of the website utilizing the deployment roles. This model utiilizes a centralized deployment architecture. 

![image](./website_automation_arch.png)

## CDK StackSet
This is a Python code (seen [here](./cdk/cdk/deployment_role_stack_set.py)) using the AWS Cloud Development Kit (CDK) to create an AWS CloudFormation StackSet for deploying Terraform deploy roles in member accounts of an organization.

creates a StackSet that will deploy a set of IAM roles to a list of accounts. The StackSet is created using the AWS CDK, which is a set of tools that allows you to create and manage AWS resources using a familiar programming language.

The StackSet is created using the following steps:

The cftemplate asset is created, which contains the CloudFormation template that will be used to deploy the StackSet.
The github_oidc_role_arn variable is created, which contains the ARN of the GitHub OIDC role.
The CFDeployStackSet stack is created, which is the StackSet that will deploy the IAM roles.
The CFDeployStackSet stack is configured with the following properties:
- permission_model: The permission model for the StackSet.
- stack_set_name: The name of the StackSet.
- capabilities: The capabilities that the StackSet will have.
- description: The description of the StackSet.
- auto_deployment: The auto-deployment settings for the StackSet.
- managed_execution: The managed execution settings for the StackSet.
- parameters: The parameters that the StackSet will use.
- stack_instances_group: The stack instances group for the StackSet.
- template_url: The URL of the CloudFormation template that will be used to deploy the StackSet.

The CFDeployStackSet stack will deploy the IAM roles to the accounts that are specified in the account_names and org_unit_ids lists. The roles will be deployed to the specified regions.

## Deployment Roles CloudFormation Template
The CloudFormation template creates an OIDC provider and **two specialized roles** for use with GitHub Actions. This replaces the previous single role that had overly broad `Action: '*'` permissions.

### Refactored Architecture
- **GitHubActionsTerraformDeploymentRole**: Specific permissions for Terraform deployments based on actual usage analysis
- **GitHubActionsCDKDeploymentRole**: Minimal permissions that delegate to CDK bootstrap roles

The template creates the following resources:

**OIDC Provider** - Used to authenticate GitHub Actions automations:
- The URL of the GitHub Actions OIDC endpoint  
- A list of thumbprints for GitHub Actions tokens
- A list of allowed audiences for the tokens

**Terraform Deployment Role** - Grants GitHub Actions the following permissions based on CloudTrail analysis:
- DynamoDB operations for state locking (`DescribeStream`, `DescribeTable`, etc.)
- KMS encryption/decryption for state files
- CloudWatch Logs for Terraform output
- SSM Parameter Store access for configuration
- ECR operations for container deployments
- EventBridge, Lambda, S3, and IAM read operations
- STS operations for role assumption

**CDK Deployment Role** - Minimal permissions that delegate to CDK bootstrap infrastructure:
- `sts:AssumeRole` only on `arn:aws:iam::${AWS::AccountId}:role/cdk-hnb659fds-deploy-role-${AWS::AccountId}-*`
- `sts:GetCallerIdentity` for identity verification
- All deployment permissions are handled by CDK's own managed roles

### Security Improvements
- **Principle of Least Privilege**: Each role only has necessary permissions
- **Separation of Concerns**: Terraform and CDK deployments are isolated  
- **Reduced Attack Surface**: CDK role has minimal direct permissions
- **Better Auditing**: Cleaner CloudTrail logs showing deployment method usage

See [REFACTORING_GUIDE.md](./REFACTORING_GUIDE.md) for detailed migration instructions.
