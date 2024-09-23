#!/bin/bash
set -eu

SITE="https://credits.apps.staging.hpc.cam.ac.uk"


# Set up some variables
CONTENT_TYPE="Content-Type: application/json"

TOKEN="CHANGE THIS AFTER REDEPLOY" 

AUTH_HEADER="Authorization: Bearer $TOKEN"

# rcp-azimuth-cloud-portal-dev 
PROJECT_ID="79b2c7925276436091fa9301c4b05fd2"

# 3. Add an account
echo "Adding an account:"
ACCOUNT_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    '{
        "name": "Tes1452 Account",
        "email": "test251@account.com"
    }' \
    $SITE/account/ | jq -r '.url')
echo "Account URL: $ACCOUNT_ID"

PROVIDER_ID="$SITE/resource_provider/1/"

echo "Adding a resource provider account:"
RPA_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    "{
        \"account\": \"$ACCOUNT_ID\", 
        \"provider\": \"$PROVIDER_ID\", 
        \"project_id\": \"$PROJECT_ID\"
    }" \
    $SITE/resource_provider_account/| jq -r '.id')
echo "Resource Provider Account ID: $RPA_ID"

START_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
END_DATE=$(date -u -d "+30 day" +"%Y-%m-%dT%H:%M:%SZ")
# 5. Add some credit allocation
echo "Adding credit allocation:"
ALLOCATION_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    "{
        \"name\": \"Test Allocation\",
        \"account\": \"$ACCOUNT_ID\",
        \"start\": \"$START_DATE\",
        \"end\": \"$END_DATE\"
    }" \
    $SITE/allocation/ | jq -r '.id')
echo "Credit Allocation ID: $ALLOCATION_ID"

# 6. Add allocation to resource
echo "Adding allocation to resources:"
curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    "{
        \"VCPU\": 10000,
        \"MEMORY_MB\": 24000000,
        \"DISK_GB\": 50000
    }" \
    $SITE/allocation/$ALLOCATION_ID/resources/
