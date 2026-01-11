#!/bin/bash
set -eux

SITE=https://credits.apps.staging.hpc.cam.ac.uk

TEST_PASSWORD="testpassword"

# Set up some variables
CONTENT_TYPE="Content-Type: application/json"

# Get a token
echo "Getting an auth token:"
TOKEN=$(curl -s -X POST -H "$CONTENT_TYPE" -d \
    "{
        \"username\": \"admin\",
        \"password\": \"$TEST_PASSWORD\"
    }" \
    $SITE/api-token-auth/ | jq -r '.token')
echo "Auth Token: $TOKEN"

AUTH_HEADER="Authorization: Bearer $TOKEN"

# 1. Add a resource provider
echo "Adding a resource provider:"
RESOURCE_PROVIDER_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    '{
        "name": "Test Provider",
        "email": "provider@test.com",
        "info_url": "http://testprovider.com"
    }' \
    $SITE/resource_provider/ | jq -r '.url')
echo "Resource Provider URL: $RESOURCE_PROVIDER_ID"

# 2. Add resource classes
echo "Adding resource classes:"
VCPU_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d '{"name": "VCPU"}' $SITE/resource_class/ | jq -r '.id')
MEMORY_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d '{"name": "MEMORY_MB"}' $SITE/resource_class/ | jq -r '.id')
DISK_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d '{"name": "DISK_GB"}' $SITE/resource_class/ | jq -r '.id')
echo "Resource Class IDs: VCPU=$VCPU_ID, MEMORY_MB=$MEMORY_ID, DISK_GB=$DISK_ID"

# 3. Add an account
echo "Adding an account:"
ACCOUNT_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    '{
        "name": "Test Account",
        "email": "test@account.com"
    }' \
    $SITE/account/ | jq -r '.url')
echo "Account URL: $ACCOUNT_ID"

# rcp-azimuth-cloud-portal-demo
PROJECT_ID="5fcc12ae513f4eaca2e0e7772f191282"

echo "Adding a resource provider account:"
RPA_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    "{
        \"account\": \"$ACCOUNT_ID\", 
        \"provider\": \"$RESOURCE_PROVIDER_ID\", 
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