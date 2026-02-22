# Refactored GitHub Actions Deployment Roles

This repository has been refactored to separate the single `GitHubActionsServiceRole` (which had overly broad `Action: '*'` permissions) into two specialized roles for better security and principle of least privilege.

## New Role Structure

### 1. GitHubActionsTerraformDeploymentRole
**Purpose**: For Terraform-based infrastructure deployments
**Role Name**: `GitHubActionsTerraformDeploymentRole-{region}-{account-id}`

**Permissions Based on Usage Analysis**:
- **DynamoDB**: State locking and table operations (`DescribeStream`, `DescribeTable`, etc.)
- **KMS**: Encryption/decryption for state files and resources
- **CloudWatch Logs**: Terraform logging and log stream creation
- **SSM Parameter Store**: Configuration and secret retrieval  
- **ECR**: Container image management for containerized deployments
- **EventBridge**: Event rule management
- **IAM**: Read-only permissions for resource discovery and role inspection
- **Lambda**: Function management and layer operations
- **S3**: Bucket configuration and resource management
- **STS**: Role assumption and caller identity verification

### 2. GitHubActionsCDKDeploymentRole  
**Purpose**: For AWS CDK deployments
**Role Name**: `GitHubActionsCDKDeploymentRole-{region}-{account-id}`

**Minimal Permissions**:
- **STS AssumeRole**: Only on CDK bootstrap deploy roles (`arn:aws:iam::{account}:role/cdk-hnb659fds-deploy-role-{account}-*`)
- **STS GetCallerIdentity**: For identity verification
- All actual deployment permissions are delegated to CDK's own bootstrap roles

## Migration Guide

### In GitHub Actions Workflows

**Before (single role)**:
```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsDeploymentRole-us-east-2-${{ secrets.AWS_ACCOUNT_ID }}
```

**After (choose appropriate role)**:

For Terraform deployments:
```yaml
- name: Configure AWS credentials for Terraform
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsTerraformDeploymentRole-us-east-2-${{ secrets.AWS_ACCOUNT_ID }}
```

For CDK deployments:
```yaml
- name: Configure AWS credentials for CDK  
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsCDKDeploymentRole-us-east-2-${{ secrets.AWS_ACCOUNT_ID }}
```

## Deployment Instructions

1. **Deploy the new roles**:
   ```bash
   aws cloudformation deploy \
     --template-file cdk/cf_templates/refactored_deployment_roles.yaml \
     --stack-name github-actions-deployment-roles \
     --capabilities CAPABILITY_IAM \
     --parameter-overrides SubjectClaimFilters="repo:cullancarey/aws_deployment_roles:*"
   ```

2. **Update your GitHub Actions workflows** to use the appropriate role for each deployment type

3. **Test deployments** with the new roles to ensure they have sufficient permissions

4. **Remove the old role** once you've confirmed the new setup works:
   ```bash
   aws cloudformation delete-stack --stack-name <old-stack-name>
   ```

## Security Benefits

- **Principle of Least Privilege**: Each role only has the minimum permissions needed for its specific use case
- **Separation of Concerns**: Terraform and CDK deployments are isolated
- **Reduced Attack Surface**: CDK role has minimal permissions since it delegates to CDK bootstrap roles
- **Better Auditing**: Cleaner CloudTrail logs showing which deployment method accessed which resources

## Permission Analysis Source

The Terraform role permissions were derived from analysis of the following usage patterns in CloudTrail logs:
- `role-api-call-event-source-name.csv`: API calls by service and action
- `role-call-count-by-account.csv`: Role usage frequency by account

Key findings:
- Terraform roles made 20,000+ DynamoDB DescribeStream calls (state locking)
- Heavy usage of KMS Decrypt (172+ calls per role) for encrypted state
- Regular CloudWatch Logs operations for Terraform output
- SSM Parameter Store access for configuration retrieval