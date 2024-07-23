#!/bin/bash

set -eux

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

PORT=8080
SITE=localhost
# Function to check if port is open
check_port() {
	nc -z localhost $PORT
	return $?
}

# Function to check HTTP status
check_http_status() {
	local status=$(curl -s -o /dev/null -w "%{http_code}" http://$SITE:$PORT/_status/)
	if [ "$status" -eq 204 ]; then
		return 0
	else
		echo "Error: Expected HTTP status code 204, but got $status"
		return 1
	fi
}

# Set variables
CHART_NAME="coral-credits"
RELEASE_NAME=$CHART_NAME
NAMESPACE=$CHART_NAME

# Install the CaaS operator from the chart we are about to ship
# Make sure to use the images that we just built
helm upgrade $RELEASE_NAME ./charts \
	--dependency-update \
	--namespace $NAMESPACE \
	--create-namespace \
	--install \
	--wait \
	--timeout 10m \
	--set-string image.tag=${GITHUB_SHA::7}

# Wait for rollout
kubectl rollout status deployment/$RELEASE_NAME -n $NAMESPACE --timeout=300s -w
# Port forward in the background
kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME $PORT:$PORT &

# Wait for port to be open
echo "Waiting for port $PORT to be available..."
for i in {1..30}; do
	if check_port; then
		echo "Port $PORT is now open"
		break
	fi
	if [ $i -eq 30 ]; then
		echo "Timeout waiting for port $PORT"
		exit 1
	fi
	sleep 1
done

# Check HTTP status with retries
echo "Checking HTTP status..."
for i in {1..10}; do
	if check_http_status; then
		echo "Success: HTTP status code is 204."
		break
	fi
	if [ $i -eq 10 ]; then
		echo "Failed to get correct HTTP status after 10 attempts"
		# Get pod logs on failure
		SELECTOR="app.kubernetes.io/name=$CHART_NAME,app.kubernetes.io/instance=$RELEASE_NAME"
		POD_NAME=$(kubectl get pods -n $NAMESPACE -l $SELECTOR -o jsonpath="{.items[0].metadata.name}")
		kubectl logs -n $NAMESPACE $POD_NAME
		exit 1
	fi
	echo "Attempt $i failed. Retrying in 3 seconds..."
	sleep 3
done

echo "Running additional tests..."

# Set up some variables
AUTH_HEADER="Authorization: Basic YWRtaW46cGFzc3dvcmQ=" # Base64 encoded "admin:password"
CONTENT_TYPE="Content-Type: application/json"

# 1. Add a resource provider
echo "Adding a resource provider:"
RESOURCE_PROVIDER_ID=$(curl -s -X POST -H "$CONTENT_TYPE" -d \
    '{
        "name": "Test Provider", 
        "email": "provider@test.com",
        "info_url": "https://testprovider.com"
    }' \
    http://$SITE:$PORT/resource_provider/ | jq -r '.id')
echo "Resource Provider ID: $RESOURCE_PROVIDER_ID"

# 2. Add resource classes
echo "Adding resource classes:"
VCPU_ID=$(curl -s -X POST -H "$CONTENT_TYPE" -d '{"name": "VCPU"}' http://$SITE:$PORT/resource_class/ | jq -r '.id')
MEMORY_ID=$(curl -s -X POST -H "$CONTENT_TYPE" -d '{"name": "MEMORY_MB"}' http://$SITE:$PORT/resource_class/ | jq -r '.id')
DISK_ID=$(curl -s -X POST -H "$CONTENT_TYPE" -d '{"name": "DISK_GB"}' http://$SITE:$PORT/resource_class/ | jq -r '.id')
echo "Resource Class IDs: VCPU=$VCPU_ID, MEMORY_MB=$MEMORY_ID, DISK_GB=$DISK_ID"

# 3. Add an account (admin endpoint)
echo "Adding an account:"
ACCOUNT_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    '{
        "name": "Test Account", 
        "email": "test@account.com"
    }' \
    http://$SITE:$PORT/admin/api/creditaccount/add/ | jq -r '.id')
echo "Account ID: $ACCOUNT_ID"

# 4. Add a resource provider account (admin endpoint)
echo "Adding a resource provider account:"
RPA_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    '{
        "account": $ACCOUNT_ID, 
        "provider": $RESOURCE_PROVIDER_ID, 
        "project_id": "test-project-id"
    }' \
    http://$SITE:$PORT/admin/api/resourceprovideraccount/add/ | jq -r '.id')
echo "Resource Provider Account ID: $RPA_ID"

# 5. Add some credit allocation (admin endpoint)
echo "Adding credit allocation:"
ALLOCATION_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    '{
        "name": "Test Allocation", 
        "account": $ACCOUNT_ID,
        "start": "2023-01-01T00:00:00Z", 
        "end": "2023-12-31T23:59:59Z"
    }' \
    http://$SITE:$PORT/admin/api/creditallocation/add/ | jq -r '.id')
echo "Credit Allocation ID: $ALLOCATION_ID"

# 6. Add allocation to resource
echo "Adding allocation to resources:"
curl -s -X POST -H "$CONTENT_TYPE" -d \
    '{
        "inventories": {
            "$VCPU_ID": 1000,
            "$MEMORY_ID": 10000,
            "$DISK_GB": 5000
        }
    }' \
    http://$SITE:$PORT/allocations/$ALLOCATION_ID/resources/

# 7. Do a consumer create
echo "Creating a consumer:"
CONSUMER_ID=$(curl -s -X POST -H "$CONTENT_TYPE" -d "{
    \"consumer_ref\": \"test-consumer\",
    \"consumer_uuid\": \"550e8400-e29b-41d4-a716-446655440000\",
    \"resource_provider_account\": $RPA_ID,
    \"user_ref\": \"test-user\",
    \"start\": \"2023-01-01T00:00:00Z\",
    \"end\": \"2023-12-31T23:59:59Z\"
}" http://$SITE:$PORT/consumer/ | jq -r '.id')
echo "Consumer ID: $CONSUMER_ID"

echo "All tests completed."
