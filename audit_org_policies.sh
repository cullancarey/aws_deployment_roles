#!/bin/bash

# AWS Organization Policies Audit Script
# This script generates a comprehensive report of all organization-level policies.
# Usage: ./audit_org_policies.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create output directory
REPORT_DIR="org_policies_audit_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

printf '%b\n' "${BLUE}========================================${NC}"
printf '%b\n' "${BLUE}AWS Organization Policies Audit${NC}"
printf '%b\n' "${BLUE}========================================${NC}"
printf '\n'

# Function to print section headers
print_section() {
    printf '\n%b\n' "${GREEN}--- $1 ---${NC}"
}

# Function to save output to file and display
save_and_display() {
    local filename="$1"
    local content="$2"
    echo "$content" | tee "$REPORT_DIR/$filename"
}

require_commands() {
    local missing=0

    for cmd in aws python3; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo -e "${RED}Missing required command: $cmd${NC}" >&2
            missing=1
        fi
    done

    if [ "$missing" -ne 0 ]; then
        exit 1
    fi
}

aws_json() {
    aws "$@" --output json
}

save_aws_json() {
    local filename="$1"
    shift

    if ! aws_json "$@" > "$REPORT_DIR/$filename"; then
        printf '{"error":"Failed to run aws %s"}\n' "$*" > "$REPORT_DIR/$filename"
        return 1
    fi
}

write_policy_details() {
    local policy_type="$1"
    local root_key="$2"
    local output_file="$3"
    local list_file="$TMP_DIR/${policy_type}_list.json"

    if ! aws_json organizations list-policies --filter "$policy_type" > "$list_file"; then
        printf '{"%s":[]}\n' "$root_key" > "$REPORT_DIR/$output_file"
        return 1
    fi

    POLICY_TYPE="$policy_type" ROOT_KEY="$root_key" LIST_FILE="$list_file" OUTPUT_FILE="$REPORT_DIR/$output_file" \
        python3 <<'PY'
import json
import os
import subprocess
import sys

policy_type = os.environ["POLICY_TYPE"]
root_key = os.environ["ROOT_KEY"]
list_file = os.environ["LIST_FILE"]
output_file = os.environ["OUTPUT_FILE"]

with open(list_file, encoding="utf-8") as handle:
    policies = json.load(handle).get("Policies", [])

items = []
for policy in policies:
    policy_id = policy["Id"]
    try:
        result = subprocess.run(
            [
                "aws",
                "organizations",
                "describe-policy",
                "--policy-id",
                policy_id,
                "--output",
                "json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        detail = json.loads(result.stdout)
    except Exception as exc:  # pragma: no cover - operational fallback
        detail = {"error": str(exc), "policy_id": policy_id, "policy_type": policy_type}
    items.append({"id": policy_id, "policy": detail})

with open(output_file, "w", encoding="utf-8") as handle:
    json.dump({root_key: items}, handle, indent=2)
    handle.write("\n")
PY
}

append_child_tree() {
    local parent_id="$1"
    local parent_name="$2"
    local parent_type="$3"
    local parent_path="$4"
    local depth="$5"
    local output_file="$6"

    local accounts_file="$TMP_DIR/accounts_${parent_id}.json"
    local ous_file="$TMP_DIR/ous_${parent_id}.json"

    if aws_json organizations list-accounts-for-parent --parent-id "$parent_id" > "$accounts_file" 2>/dev/null; then
        PARENT_ID="$parent_id" PARENT_NAME="$parent_name" PARENT_TYPE="$parent_type" PARENT_PATH="$parent_path" DEPTH="$depth" JSON_FILE="$accounts_file" \
            python3 <<'PY' >> "$output_file"
import json
import os

with open(os.environ["JSON_FILE"], encoding="utf-8") as handle:
    accounts = json.load(handle).get("Accounts", [])

for account in accounts:
    print(json.dumps({
        "id": account.get("Id"),
        "name": account.get("Name"),
        "arn": account.get("Arn"),
        "email": account.get("Email"),
        "status": account.get("Status"),
        "parent_id": os.environ["PARENT_ID"],
        "parent_name": os.environ["PARENT_NAME"],
        "parent_type": os.environ["PARENT_TYPE"],
        "path": os.environ["PARENT_PATH"],
        "depth": int(os.environ["DEPTH"]),
        "node_type": "ACCOUNT",
    }))
PY
    fi

    if ! aws_json organizations list-organizational-units-for-parent --parent-id "$parent_id" > "$ous_file" 2>/dev/null; then
        return
    fi

    local child_list_file="$TMP_DIR/ous_${parent_id}_list.tsv"

    python3 - "$ous_file" <<'PY' > "$child_list_file"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    for ou in json.load(handle).get("OrganizationalUnits", []):
        print(f"{ou.get('Id', '')}\t{ou.get('Name', '')}\t{ou.get('Arn', '')}")
PY

    while IFS=$'\t' read -r child_id child_name child_arn; do
        [ -z "$child_id" ] && continue
        local child_path="$parent_path/$child_name"

        CHILD_ID="$child_id" CHILD_NAME="$child_name" CHILD_ARN="$child_arn" PARENT_ID="$parent_id" PARENT_NAME="$parent_name" PARENT_TYPE="$parent_type" CHILD_PATH="$child_path" DEPTH="$depth" \
            python3 <<'PY' >> "$output_file"
import json
import os

print(json.dumps({
    "id": os.environ["CHILD_ID"],
    "name": os.environ["CHILD_NAME"],
    "arn": os.environ["CHILD_ARN"],
    "parent_id": os.environ["PARENT_ID"],
    "parent_name": os.environ["PARENT_NAME"],
    "parent_type": os.environ["PARENT_TYPE"],
    "path": os.environ["CHILD_PATH"],
    "depth": int(os.environ["DEPTH"]),
    "node_type": "ORGANIZATIONAL_UNIT",
}))
PY

        append_child_tree "$child_id" "$child_name" "ORGANIZATIONAL_UNIT" "$child_path" "$((depth + 1))" "$output_file"
    done < "$child_list_file"
}

write_org_tree() {
    local roots_file="$TMP_DIR/roots.json"
    local lines_file="$TMP_DIR/org_tree_lines.jsonl"

    : > "$lines_file"
    if ! aws_json organizations list-roots > "$roots_file"; then
        printf '{"organization_tree":[],"error":"Failed to list organization roots"}\n' > "$REPORT_DIR/03_organizational_units.json"
        return 1
    fi

    local root_list_file="$TMP_DIR/root_list.tsv"

    python3 - "$roots_file" <<'PY' > "$root_list_file"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    for root in json.load(handle).get("Roots", []):
        print(f"{root.get('Id', '')}\t{root.get('Name', '')}\t{root.get('Arn', '')}")
PY

    while IFS=$'\t' read -r root_id root_name root_arn; do
        [ -z "$root_id" ] && continue

        ROOT_ID="$root_id" ROOT_NAME="$root_name" ROOT_ARN="$root_arn" \
            python3 <<'PY' >> "$lines_file"
import json
import os

print(json.dumps({
    "id": os.environ["ROOT_ID"],
    "name": os.environ["ROOT_NAME"],
    "arn": os.environ["ROOT_ARN"],
    "path": os.environ["ROOT_NAME"],
    "depth": 0,
    "node_type": "ROOT",
}))
PY

        append_child_tree "$root_id" "$root_name" "ROOT" "$root_name" 1 "$lines_file"
    done < "$root_list_file"

    python3 - "$lines_file" "$REPORT_DIR/03_organizational_units.json" <<'PY'
import json
import sys

input_file, output_file = sys.argv[1], sys.argv[2]
items = []
with open(input_file, encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if line:
            items.append(json.loads(line))

with open(output_file, "w", encoding="utf-8") as handle:
    json.dump({"organization_tree": items}, handle, indent=2)
    handle.write("\n")
PY
}

write_policy_targets() {
    local enabled_types_file="$TMP_DIR/enabled_policy_types.txt"
    local policy_ids_file="$TMP_DIR/policy_ids.txt"
    local results_file="$TMP_DIR/policy_targets.jsonl"

    : > "$policy_ids_file"
    : > "$results_file"

    python3 - "$REPORT_DIR/01_organization_info.json" <<'PY' > "$enabled_types_file"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    organization = json.load(handle).get("Organization", {})

for policy_type in organization.get("AvailablePolicyTypes", []):
    if policy_type.get("Status") == "ENABLED":
        print(policy_type.get("Type", ""))
PY

    while IFS= read -r policy_type; do
        [ -z "$policy_type" ] && continue
        aws organizations list-policies --filter "$policy_type" --query 'Policies[].Id' --output text 2>/dev/null | tr '\t' '\n' >> "$policy_ids_file"
    done < "$enabled_types_file"

    sort -u "$policy_ids_file" | while IFS= read -r policy_id; do
        [ -z "$policy_id" ] && continue
        POLICY_ID="$policy_id" \
            python3 <<'PY' >> "$results_file"
import json
import os
import subprocess

policy_id = os.environ["POLICY_ID"]
try:
    result = subprocess.run(
        [
            "aws",
            "organizations",
            "list-targets-for-policy",
            "--policy-id",
            policy_id,
            "--output",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    targets = json.loads(result.stdout).get("Targets", [])
except Exception as exc:  # pragma: no cover - operational fallback
    targets = [{"error": str(exc)}]

if targets:
    print(json.dumps({"policy_id": policy_id, "targets": targets}))
PY
    done

    python3 - "$results_file" "$REPORT_DIR/08_policy_targets.json" <<'PY'
import json
import sys

input_file, output_file = sys.argv[1], sys.argv[2]
items = []
with open(input_file, encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if line:
            items.append(json.loads(line))

with open(output_file, "w", encoding="utf-8") as handle:
    json.dump({"policy_targets": items}, handle, indent=2)
    handle.write("\n")
PY
}

require_commands

# 1. Get Organization Info
print_section "Organization Details"
save_aws_json "01_organization_info.json" organizations describe-organization || true

# 2. Get all accounts
print_section "Organization Accounts"
ACCOUNTS=$(aws organizations list-accounts --query 'Accounts[].[Id,Name,Status]' --output table 2>/dev/null || echo "Failed to list accounts")
save_and_display "02_accounts.txt" "$ACCOUNTS"

# 3. Get all OUs (Organizational Units)
print_section "Organizational Units (OUs)"
if ! write_org_tree; then
    printf '{"organization_tree":[],"error":"Failed to build organization tree"}\n' > "$REPORT_DIR/03_organizational_units.json"
fi
cat "$REPORT_DIR/03_organizational_units.json"

# 4. Service Control Policies (SCPs)
print_section "Service Control Policies (SCPs)"
echo "Fetching SCPs..."

# List all SCPs
SCPS=$(aws organizations list-policies --filter SERVICE_CONTROL_POLICY --query 'Policies[].[Id,Name,Type,AwsManaged]' --output table 2>/dev/null || echo "Failed to list SCPs")
save_and_display "04_scps_list.txt" "$SCPS"

# Get detailed SCP content
write_policy_details "SERVICE_CONTROL_POLICY" "service_control_policies" "04_scps_detailed.json" || true
echo "Saved detailed SCPs to 04_scps_detailed.json"

# 5. Tag Policies
print_section "Tag Policies"
TAG_POLICIES=$(aws organizations list-policies --filter TAG_POLICY --query 'Policies[].[Id,Name,Type,AwsManaged]' --output table 2>/dev/null || echo "Failed to list tag policies")
save_and_display "05_tag_policies_list.txt" "$TAG_POLICIES"

# Get detailed tag policy content
write_policy_details "TAG_POLICY" "tag_policies" "05_tag_policies_detailed.json" || true
echo "Saved detailed tag policies to 05_tag_policies_detailed.json"

# 6. Backup Policies
print_section "Backup Policies"
BACKUP_POLICIES=$(aws organizations list-policies --filter BACKUP_POLICY --query 'Policies[].[Id,Name,Type,AwsManaged]' --output table 2>/dev/null || echo "Failed to list backup policies")
save_and_display "06_backup_policies_list.txt" "$BACKUP_POLICIES"

# Get detailed backup policy content
write_policy_details "BACKUP_POLICY" "backup_policies" "06_backup_policies_detailed.json" || true
echo "Saved detailed backup policies to 06_backup_policies_detailed.json"

# 7. AI Services Opt-out Policies
print_section "AI Services Opt-out Policies"
AI_POLICIES=$(aws organizations list-policies --filter AISERVICES_OPT_OUT_POLICY --query 'Policies[].[Id,Name,Type,AwsManaged]' --output table 2>/dev/null || echo "Failed to list AI opt-out policies")
save_and_display "07_ai_optout_policies_list.txt" "$AI_POLICIES"
write_policy_details "AISERVICES_OPT_OUT_POLICY" "ai_services_opt_out_policies" "07_ai_optout_policies_detailed.json" || true
echo "Saved detailed AI opt-out policies to 07_ai_optout_policies_detailed.json"

# 8. Policy targets (what policies are attached to what)
print_section "Policy Targets (Policy Attachments)"
write_policy_targets
echo "Saved policy targets to 08_policy_targets.json"

# 9. Create a summary report
print_section "Generating Summary Report"
{
    echo "# AWS Organization Policies Audit Report"
    echo "Generated: $(date)"
    echo ""
    echo "## Summary"
    echo ""
    echo "### Organization Details"
    echo "See: 01_organization_info.json"
    echo ""
    echo "### Accounts"
    echo "See: 02_accounts.txt"
    echo ""
    echo "### Organizational Units"
    echo "See: 03_organizational_units.json"
    echo ""
    echo "### Service Control Policies (SCPs)"
    echo "- List: 04_scps_list.txt"
    echo "- Detailed: 04_scps_detailed.json"
    echo ""
    echo "### Tag Policies"
    echo "- List: 05_tag_policies_list.txt"
    echo "- Detailed: 05_tag_policies_detailed.json"
    echo ""
    echo "### Backup Policies"
    echo "- List: 06_backup_policies_list.txt"
    echo "- Detailed: 06_backup_policies_detailed.json"
    echo ""
    echo "### AI Services Opt-out Policies"
    echo "- List: 07_ai_optout_policies_list.txt"
    echo "- Detailed: 07_ai_optout_policies_detailed.json"
    echo ""
    echo "### Policy Targets (Attachments)"
    echo "See: 08_policy_targets.json"
    echo ""
    echo "## Next Steps"
    echo "1. Review the policy files above"
    echo "2. Identify policies to migrate to CDK"
    echo "3. Create CDK constructs for each policy type"
    echo "4. Use create_org_policies_cdk.py to generate CDK code"
} > "$REPORT_DIR/README.md"

printf '\n%b\n' "${YELLOW}========================================${NC}"
printf '%b\n' "${YELLOW}Audit Complete!${NC}"
printf '%b\n' "${YELLOW}========================================${NC}"
printf '\n'
printf '%b\n' "${GREEN}Report saved to: ${REPORT_DIR}/${NC}"
printf '\n'
echo "Files generated:"
ls -lh "$REPORT_DIR/" | tail -n +2 | awk '{print "  " $9}'
echo ""
printf '%b\n' "${BLUE}Next steps:${NC}"
echo "1. Review the policies in the generated reports"
echo "2. Identify which policies you want to manage with CDK"
echo "3. We can create CDK constructs for each policy type"
