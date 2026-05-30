from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_organizations as organizations
from aws_cdk import custom_resources as cr
from constructs import Construct


class OrganizationPolicyGuardrailsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        root_id: str,
        cloudtrail_trail_name: str,
        cloudtrail_logs_bucket_name: str,
        approved_regions: list[str],
        admin_permission_set_name: str,
        legacy_region_policy_id: str | None = None,
        legacy_region_migration_phase: str = "observe",
        full_aws_access_policy_id: str | None = None,
        full_aws_access_detach_target_ids: list[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if legacy_region_migration_phase not in {"observe", "cutover"}:
            raise ValueError(
                "legacy_region_migration_phase must be 'observe' or 'cutover'"
            )

        full_aws_access_detach_target_ids = full_aws_access_detach_target_ids or []

        admin_role_arns = [
            (
                "arn:aws:iam::*:role/aws-reserved/sso.amazonaws.com/"
                f"AWSReservedSSO_{admin_permission_set_name}_*"
            ),
            (
                "arn:aws:iam::*:role/aws-reserved/sso.amazonaws.com/*/"
                f"AWSReservedSSO_{admin_permission_set_name}_*"
            ),
        ]
        automation_role_arns = [
            "arn:aws:iam::*:role/cdk-hnb659fds-*",
            "arn:aws:iam::*:role/GitHubActionsCDKDeploymentRole-*",
            "arn:aws:iam::*:role/GitHubActionsTerraformDeploymentRole-*",
        ]
        privileged_principal_arns = admin_role_arns + automation_role_arns

        approved_regions_policy = organizations.CfnPolicy(
            self,
            "ApprovedRegionsPolicy",
            name="Deny-Outside-Approved-Regions",
            description=(
                "Deny access to unapproved AWS regions while preserving global "
                "control-plane services required for account and identity management."
            ),
            type="SERVICE_CONTROL_POLICY",
            content={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "DenyOutsideApprovedRegions",
                        "Effect": "Deny",
                        "NotAction": [
                            "account:*",
                            "aws-portal:*",
                            "billing:*",
                            "budgets:*",
                            "ce:*",
                            "chime:*",
                            "cloudfront:*",
                            "cur:*",
                            "directconnect:*",
                            "ec2:DescribeRegions",
                            "globalaccelerator:*",
                            "health:*",
                            "iam:*",
                            "importexport:*",
                            "organizations:*",
                            "payments:*",
                            "pricing:*",
                            "route53:*",
                            "route53domains:*",
                            "route53-recovery-cluster:*",
                            "route53-recovery-control-config:*",
                            "route53-recovery-readiness:*",
                            "s3:GetAccountPublicAccessBlock",
                            "s3:ListAllMyBuckets",
                            "s3:PutAccountPublicAccessBlock",
                            "shield:*",
                            "sts:*",
                            "support:*",
                            "tax:*",
                            "trustedadvisor:*",
                            "waf:*",
                            "wafv2:*",
                        ],
                        "Resource": "*",
                        "Condition": {
                            "StringNotEquals": {
                                "aws:RequestedRegion": approved_regions,
                            }
                        },
                    }
                ],
            },
            target_ids=[root_id],
        )

        root_user_policy = organizations.CfnPolicy(
            self,
            "RootUserRestrictionsPolicy",
            name="Deny-Root-User-Day-To-Day-Access",
            description=(
                "Deny routine AWS API usage by the root user while preserving a small "
                "set of billing and support workflows."
            ),
            type="SERVICE_CONTROL_POLICY",
            content={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "DenyRootUserRoutineAccess",
                        "Effect": "Deny",
                        "NotAction": [
                            "account:Get*",
                            "account:List*",
                            "aws-portal:View*",
                            "billing:*",
                            "budgets:ViewBudget",
                            "ce:Get*",
                            "ce:List*",
                            "payments:*",
                            "support:*",
                            "tax:*",
                        ],
                        "Resource": "*",
                        "Condition": {
                            "ArnLike": {"aws:PrincipalArn": "arn:aws:iam::*:root"}
                        },
                    }
                ],
            },
            target_ids=[root_id],
        )

        cloudtrail_trail_arn = (
            f"arn:aws:cloudtrail:*:{self.account}:trail/{cloudtrail_trail_name}"
        )
        cloudtrail_logs_bucket_arn = f"arn:aws:s3:::{cloudtrail_logs_bucket_name}"

        audit_protection_policy = organizations.CfnPolicy(
            self,
            "AuditProtectionPolicy",
            name="Protect-Organization-Audit-Resources",
            description=(
                "Prevent changes to organization CloudTrail resources and log storage "
                "except through the designated administrator and deployment paths."
            ),
            type="SERVICE_CONTROL_POLICY",
            content={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "ProtectOrganizationTrail",
                        "Effect": "Deny",
                        "Action": [
                            "cloudtrail:AddTags",
                            "cloudtrail:DeleteTrail",
                            "cloudtrail:PutEventSelectors",
                            "cloudtrail:PutInsightSelectors",
                            "cloudtrail:PutResourcePolicy",
                            "cloudtrail:RemoveTags",
                            "cloudtrail:StopLogging",
                            "cloudtrail:UpdateTrail",
                        ],
                        "Resource": cloudtrail_trail_arn,
                        "Condition": {
                            "ArnNotLike": {
                                "aws:PrincipalArn": privileged_principal_arns
                            }
                        },
                    },
                    {
                        "Sid": "ProtectOrganizationTrailLogBucket",
                        "Effect": "Deny",
                        "Action": [
                            "s3:DeleteBucket",
                            "s3:DeleteBucketPolicy",
                            "s3:DeleteObject",
                            "s3:DeleteObjectVersion",
                            "s3:DeleteBucketOwnershipControls",
                            "s3:DeleteBucketPublicAccessBlock",
                            "s3:PutBucketAcl",
                            "s3:PutBucketLogging",
                            "s3:PutBucketOwnershipControls",
                            "s3:PutBucketPolicy",
                            "s3:PutBucketPublicAccessBlock",
                            "s3:PutBucketVersioning",
                            "s3:PutEncryptionConfiguration",
                            "s3:PutLifecycleConfiguration",
                        ],
                        "Resource": [
                            cloudtrail_logs_bucket_arn,
                            f"{cloudtrail_logs_bucket_arn}/*",
                        ],
                        "Condition": {
                            "ArnNotLike": {
                                "aws:PrincipalArn": privileged_principal_arns
                            }
                        },
                    },
                ],
            },
            target_ids=[root_id],
        )

        organization_membership_policy = organizations.CfnPolicy(
            self,
            "OrganizationMembershipProtectionPolicy",
            name="Protect-Organization-Membership-And-Policies",
            description=(
                "Restrict organization membership and policy administration changes to "
                "the designated administrator and deployment paths."
            ),
            type="SERVICE_CONTROL_POLICY",
            content={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "ProtectOrganizationAdministration",
                        "Effect": "Deny",
                        "Action": [
                            "account:CloseAccount",
                            "organizations:AcceptHandshake",
                            "organizations:AttachPolicy",
                            "organizations:CreateAccount",
                            "organizations:CreateGovCloudAccount",
                            "organizations:CreateOrganization",
                            "organizations:CreateOrganizationalUnit",
                            "organizations:CreatePolicy",
                            "organizations:DeclineHandshake",
                            "organizations:DeregisterDelegatedAdministrator",
                            "organizations:DeleteOrganization",
                            "organizations:DeleteOrganizationalUnit",
                            "organizations:DeletePolicy",
                            "organizations:DeleteResourcePolicy",
                            "organizations:DetachPolicy",
                            "organizations:DisableAWSServiceAccess",
                            "organizations:EnableAWSServiceAccess",
                            "organizations:InviteAccountToOrganization",
                            "organizations:LeaveOrganization",
                            "organizations:MoveAccount",
                            "organizations:PutResourcePolicy",
                            "organizations:RegisterDelegatedAdministrator",
                            "organizations:RemoveAccountFromOrganization",
                            "organizations:UpdateOrganizationalUnit",
                            "organizations:UpdatePolicy",
                        ],
                        "Resource": "*",
                        "Condition": {
                            "ArnNotLike": {
                                "aws:PrincipalArn": privileged_principal_arns
                            }
                        },
                    }
                ],
            },
            target_ids=[root_id],
        )

        organizations_api_policy = cr.AwsCustomResourcePolicy.from_statements(
            [
                iam.PolicyStatement(
                    actions=[
                        "organizations:AttachPolicy",
                        "organizations:DetachPolicy",
                    ],
                    resources=["*"],
                )
            ]
        )

        full_aws_access_root_attachment = None
        if full_aws_access_policy_id:
            full_aws_access_root_attachment = cr.AwsCustomResource(
                self,
                "EnsureFullAWSAccessRootAttachment",
                on_create=cr.AwsSdkCall(
                    service="Organizations",
                    action="attachPolicy",
                    parameters={
                        "PolicyId": full_aws_access_policy_id,
                        "TargetId": root_id,
                    },
                    physical_resource_id=cr.PhysicalResourceId.of(
                        f"attach-{full_aws_access_policy_id}-{root_id}"
                    ),
                    ignore_error_codes_matching="DuplicatePolicyAttachmentException",
                ),
                on_update=cr.AwsSdkCall(
                    service="Organizations",
                    action="attachPolicy",
                    parameters={
                        "PolicyId": full_aws_access_policy_id,
                        "TargetId": root_id,
                    },
                    physical_resource_id=cr.PhysicalResourceId.of(
                        f"attach-{full_aws_access_policy_id}-{root_id}"
                    ),
                    ignore_error_codes_matching="DuplicatePolicyAttachmentException",
                ),
                policy=organizations_api_policy,
                install_latest_aws_sdk=False,
            )

            for target_id in full_aws_access_detach_target_ids:
                detach_resource = cr.AwsCustomResource(
                    self,
                    f"DetachFullAWSAccess{self._safe_logical_id(target_id)}",
                    on_create=cr.AwsSdkCall(
                        service="Organizations",
                        action="detachPolicy",
                        parameters={
                            "PolicyId": full_aws_access_policy_id,
                            "TargetId": target_id,
                        },
                        physical_resource_id=cr.PhysicalResourceId.of(
                            f"detach-{full_aws_access_policy_id}-{target_id}"
                        ),
                        ignore_error_codes_matching="PolicyNotAttachedException|ConstraintViolationException",
                    ),
                    on_update=cr.AwsSdkCall(
                        service="Organizations",
                        action="detachPolicy",
                        parameters={
                            "PolicyId": full_aws_access_policy_id,
                            "TargetId": target_id,
                        },
                        physical_resource_id=cr.PhysicalResourceId.of(
                            f"detach-{full_aws_access_policy_id}-{target_id}"
                        ),
                        ignore_error_codes_matching="PolicyNotAttachedException|ConstraintViolationException",
                    ),
                    policy=organizations_api_policy,
                    install_latest_aws_sdk=False,
                )
                detach_resource.node.add_dependency(full_aws_access_root_attachment)

        if legacy_region_policy_id and legacy_region_migration_phase == "cutover":
            legacy_region_detach = cr.AwsCustomResource(
                self,
                "DetachLegacyRegionPolicyFromRoot",
                on_create=cr.AwsSdkCall(
                    service="Organizations",
                    action="detachPolicy",
                    parameters={
                        "PolicyId": legacy_region_policy_id,
                        "TargetId": root_id,
                    },
                    physical_resource_id=cr.PhysicalResourceId.of(
                        f"detach-{legacy_region_policy_id}-{root_id}"
                    ),
                    ignore_error_codes_matching="PolicyNotAttachedException",
                ),
                on_update=cr.AwsSdkCall(
                    service="Organizations",
                    action="detachPolicy",
                    parameters={
                        "PolicyId": legacy_region_policy_id,
                        "TargetId": root_id,
                    },
                    physical_resource_id=cr.PhysicalResourceId.of(
                        f"detach-{legacy_region_policy_id}-{root_id}"
                    ),
                    ignore_error_codes_matching="PolicyNotAttachedException",
                ),
                policy=organizations_api_policy,
                install_latest_aws_sdk=False,
            )
            legacy_region_detach.node.add_dependency(approved_regions_policy)

        CfnOutput(
            self,
            "ApprovedRegionsPolicyId",
            value=approved_regions_policy.attr_id,
        )
        CfnOutput(
            self,
            "RootUserRestrictionsPolicyId",
            value=root_user_policy.attr_id,
        )
        CfnOutput(
            self,
            "AuditProtectionPolicyId",
            value=audit_protection_policy.attr_id,
        )
        CfnOutput(
            self,
            "OrganizationMembershipProtectionPolicyId",
            value=organization_membership_policy.attr_id,
        )
        CfnOutput(
            self,
            "LegacyRegionMigrationPhase",
            value=legacy_region_migration_phase,
        )
        CfnOutput(
            self,
            "FullAWSAccessCleanupTargets",
            value=str(len(full_aws_access_detach_target_ids)),
        )

    @staticmethod
    def _safe_logical_id(value: str) -> str:
        sanitized = "".join(character for character in value if character.isalnum())
        return sanitized or "Target"
