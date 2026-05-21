#!/usr/bin/env bash

set -euo pipefail

############################################
# ========= REQUIRED VARIABLES ============
############################################

# CloudTrail
TRAIL_NAME="org-management-trail"
CLOUDTRAIL_BUCKET="org-cloudtrail-logs-362055466028"

# KMS (leave empty if not used)
KMS_KEY_ID=""

# Athena / Glue
ATHENA_DATABASE="default"
ATHENA_TABLE="cloudtrail_logs"
ATHENA_WORKGROUP="primary"

############################################
# ========= OPTIONAL REGION CONFIG ========
############################################

AWS_REGION="us-east-2"
export AWS_DEFAULT_REGION="$AWS_REGION"

############################################
# ========= OUTPUT DIRECTORY ==============
############################################

OUTPUT_DIR="output"
mkdir -p "$OUTPUT_DIR"

echo "Using region: $AWS_REGION"
echo "Writing outputs to: $OUTPUT_DIR"
echo ""

############################################
# ========= S3 BUCKET DETAILS =============
############################################

echo "Collecting S3 bucket details..."

aws s3api get-bucket-location \
  --bucket "$CLOUDTRAIL_BUCKET" \
  > "$OUTPUT_DIR/s3_bucket_location.json" 2>/dev/null || true

aws s3api get-bucket-versioning \
  --bucket "$CLOUDTRAIL_BUCKET" \
  > "$OUTPUT_DIR/s3_bucket_versioning.json" 2>/dev/null || true

aws s3api get-bucket-encryption \
  --bucket "$CLOUDTRAIL_BUCKET" \
  > "$OUTPUT_DIR/s3_bucket_encryption.json" 2>/dev/null || true

aws s3api get-bucket-policy \
  --bucket "$CLOUDTRAIL_BUCKET" \
  > "$OUTPUT_DIR/s3_bucket_policy.json" 2>/dev/null || true

aws s3api get-public-access-block \
  --bucket "$CLOUDTRAIL_BUCKET" \
  > "$OUTPUT_DIR/s3_bucket_public_access_block.json" 2>/dev/null || true

aws s3api get-bucket-logging \
  --bucket "$CLOUDTRAIL_BUCKET" \
  > "$OUTPUT_DIR/s3_bucket_logging.json" 2>/dev/null || true

aws s3api get-bucket-lifecycle-configuration \
  --bucket "$CLOUDTRAIL_BUCKET" \
  > "$OUTPUT_DIR/s3_bucket_lifecycle.json" 2>/dev/null || true

aws s3api get-bucket-tagging \
  --bucket "$CLOUDTRAIL_BUCKET" \
  > "$OUTPUT_DIR/s3_bucket_tags.json" 2>/dev/null || true

aws s3api get-bucket-ownership-controls \
  --bucket "$CLOUDTRAIL_BUCKET" \
  > "$OUTPUT_DIR/s3_bucket_ownership_controls.json" 2>/dev/null || true


############################################
# ========= KMS (OPTIONAL) ================
############################################

if [[ -n "$KMS_KEY_ID" ]]; then
  echo "Collecting KMS details..."

  aws kms describe-key \
    --key-id "$KMS_KEY_ID" \
    > "$OUTPUT_DIR/kms_describe_key.json"

  aws kms get-key-policy \
    --key-id "$KMS_KEY_ID" \
    --policy-name default \
    > "$OUTPUT_DIR/kms_key_policy.json"
fi


############################################
# ========= CLOUDTRAIL DETAILS ============
############################################

echo "Collecting CloudTrail details..."

aws cloudtrail describe-trails \
  > "$OUTPUT_DIR/cloudtrail_describe_trails.json"

aws cloudtrail get-trail \
  --name "$TRAIL_NAME" \
  > "$OUTPUT_DIR/cloudtrail_get_trail.json"

aws cloudtrail get-event-selectors \
  --trail-name "$TRAIL_NAME" \
  > "$OUTPUT_DIR/cloudtrail_event_selectors.json"

aws cloudtrail get-trail-status \
  --name "$TRAIL_NAME" \
  > "$OUTPUT_DIR/cloudtrail_status.json"


############################################
# ========= ATHENA DETAILS ================
############################################

echo "Collecting Athena details..."

aws athena list-databases \
  --catalog-name AwsDataCatalog \
  > "$OUTPUT_DIR/athena_list_databases.json"

if [[ -n "$ATHENA_DATABASE" ]]; then

  aws athena get-database \
    --catalog-name AwsDataCatalog \
    --database-name "$ATHENA_DATABASE" \
    > "$OUTPUT_DIR/athena_get_database.json" 2>/dev/null || true

  aws athena list-table-metadata \
    --catalog-name AwsDataCatalog \
    --database-name "$ATHENA_DATABASE" \
    > "$OUTPUT_DIR/athena_list_tables.json" 2>/dev/null || true

  if [[ -n "$ATHENA_TABLE" ]]; then
    aws athena get-table-metadata \
      --catalog-name AwsDataCatalog \
      --database-name "$ATHENA_DATABASE" \
      --table-name "$ATHENA_TABLE" \
      > "$OUTPUT_DIR/athena_get_table.json" 2>/dev/null || true
  fi
fi


############################################
# ========= ATHENA WORKGROUP ==============
############################################

aws athena list-work-groups \
  > "$OUTPUT_DIR/athena_list_workgroups.json"

if [[ -n "$ATHENA_WORKGROUP" ]]; then
  aws athena get-work-group \
    --work-group "$ATHENA_WORKGROUP" \
    > "$OUTPUT_DIR/athena_get_workgroup.json" 2>/dev/null || true
fi


############################################
# ========= GLUE (IF USED) ================
############################################

echo "Collecting Glue metadata..."

aws glue get-databases \
  > "$OUTPUT_DIR/glue_get_databases.json"

if [[ -n "$ATHENA_DATABASE" ]]; then
  aws glue get-tables \
    --database-name "$ATHENA_DATABASE" \
    > "$OUTPUT_DIR/glue_get_tables.json" 2>/dev/null || true

  if [[ -n "$ATHENA_TABLE" ]]; then
    aws glue get-table \
      --database-name "$ATHENA_DATABASE" \
      --name "$ATHENA_TABLE" \
      > "$OUTPUT_DIR/glue_get_table.json" 2>/dev/null || true
  fi
fi

echo ""
echo "Done. Outputs written to $OUTPUT_DIR/"