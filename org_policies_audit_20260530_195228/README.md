# AWS Organization Policies Audit Report
Generated: Sat May 30 19:52:55 EDT 2026

## Summary

### Organization Details
See: 01_organization_info.json

### Accounts
See: 02_accounts.txt

### Organizational Units
See: 03_organizational_units.json

### Service Control Policies (SCPs)
- List: 04_scps_list.txt
- Detailed: 04_scps_detailed.json

### Tag Policies
- List: 05_tag_policies_list.txt
- Detailed: 05_tag_policies_detailed.json

### Backup Policies
- List: 06_backup_policies_list.txt
- Detailed: 06_backup_policies_detailed.json

### AI Services Opt-out Policies
- List: 07_ai_optout_policies_list.txt
- Detailed: 07_ai_optout_policies_detailed.json

### Policy Targets (Attachments)
See: 08_policy_targets.json

## Next Steps
1. Review the policy files above
2. Identify policies to migrate to CDK
3. Create CDK constructs for each policy type
4. Use create_org_policies_cdk.py to generate CDK code
