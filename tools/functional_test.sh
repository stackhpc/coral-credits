#!/bin/bash

set -eux

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

PORT=443
SITE=localhost
# Function to check if port is open
check_port() {
	nc -z localhost $PORT
	return $?
}

# Function to check HTTP status
check_http_status() {
	local status=$(curl -s -o /dev/null -w "%{http_code}" https://$SITE/_status/)
	if [ "$status" -eq 204 ]; then
		return 0
	else
		echo "Error: Expected HTTP status code 204, but got $status"
		return 1
	fi
}

# Set variables
CHART_NAME="coral-credits"
CERT_NAME="coral-secret"
RELEASE_NAME=$CHART_NAME
NAMESPACE=$CHART_NAME
TEST_PASSWORD="testpassword"

# Install nginx
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $CERT_NAME.key -out $CERT_NAME.crt -subj "/CN=${SITE}/O=${SITE}" -addext "subjectAltName = DNS:${SITE}"

# Create cluster secret
kubectl create secret tls $CERT_NAME --key $CERT_NAME.key --cert $CERT_NAME.crt

# Install the CaaS operator from the chart we are about to ship
# Make sure to use the images that we just built
helm upgrade $RELEASE_NAME ./charts \
	--dependency-update \
	--namespace $NAMESPACE \
	--create-namespace \
	--install \
	--wait \
	--timeout 3m \
	--set-string image.tag=${GITHUB_SHA::7} \
    --set settings.superuserPassword=$TEST_PASSWORD \
    --set ingress.host=$SITE \
    --set ingress.tls.secretName=$CERT_NAME \

# Wait for rollout
kubectl rollout status deployment/$RELEASE_NAME -n $NAMESPACE --timeout=300s -w

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
CONTENT_TYPE="Content-Type: application/json"

# Get a token
echo "Getting an auth token:"
TOKEN=$(curl -s -X POST -H "$CONTENT_TYPE" -d \
    "{
        \"username\": \"admin\", 
        \"password\": \"$TEST_PASSWORD\"
    }" \
    https://$SITE/api-token-auth/ | jq -r '.token')
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
    https://$SITE/resource_provider/ | jq -r '.url')
echo "Resource Provider URL: $RESOURCE_PROVIDER_ID"

# 2. Add resource classes
echo "Adding resource classes:"
VCPU_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d '{"name": "VCPU"}' https://$SITE/resource_class/ | jq -r '.id')
MEMORY_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d '{"name": "MEMORY_MB"}' https://$SITE/resource_class/ | jq -r '.id')
DISK_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d '{"name": "DISK_GB"}' https://$SITE/resource_class/ | jq -r '.id')
echo "Resource Class IDs: VCPU=$VCPU_ID, MEMORY_MB=$MEMORY_ID, DISK_GB=$DISK_ID"

# 3. Add an account
echo "Adding an account:"
ACCOUNT_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    '{
        "name": "Test Account", 
        "email": "test@account.com"
    }' \
    https://$SITE/account/ | jq -r '.url')
echo "Account URL: $ACCOUNT_ID"

PROJECT_ID="20354d7a-e4fe-47af-8ff6-187bca92f3f9"
# 4. Add a resource provider account 
echo "Adding a resource provider account:"
RPA_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    "{
        \"account\": \"$ACCOUNT_ID\", 
        \"provider\": \"$RESOURCE_PROVIDER_ID\", 
        \"project_id\": \"$PROJECT_ID\"
    }" \
    https://$SITE/resource_provider_account/| jq -r '.id')
echo "Resource Provider Account ID: $RPA_ID"

START_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
END_DATE=$(date -u -d "+1 day" +"%Y-%m-%dT%H:%M:%SZ")
# 5. Add some credit allocation
echo "Adding credit allocation:"
ALLOCATION_ID=$(curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    "{
        \"name\": \"Test Allocation\", 
        \"account\": \"$ACCOUNT_ID\",
        \"start\": \"$START_DATE\", 
        \"end\": \"$END_DATE\"
    }" \
    https://$SITE/allocation/ | jq -r '.id')
echo "Credit Allocation ID: $ALLOCATION_ID"

# 6. Add allocation to resource
echo "Adding allocation to resources:"
curl -s -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d \
    "{
        \"VCPU\": 100,
        \"MEMORY_MB\": 24000,
        \"DISK_GB\": 5000
    }" \
    https://$SITE/allocation/$ALLOCATION_ID/resources/

# 7. Do a consumer create
echo "Creating a consumer:"
RESPONSE=$(curl -s -w "%{http_code}" -X POST -H "$AUTH_HEADER" -H "$CONTENT_TYPE" -d "{
        \"context\": {
            \"user_id\": \"caa8b54a-eb5e-4134-8ae2-a3946a428ec7\",
            \"project_id\": \"$PROJECT_ID\",
            \"auth_url\": \"http://api.example.com:5000/v3\",
            \"region_name\": \"RegionOne\"
        },
        \"lease\": {
            \"id\": \"e96b5a17-ada0-4034-a5ea-34db024b8e04\",
            \"name\": \"my_new_lease\",
            \"start_date\": \"$START_DATE\",
            \"end_date\": \"$END_DATE\",
            \"reservations\": [
                {
                    \"resource_type\": \"physical:host\",
                    \"min\": 1,
                    \"max\": 3
                }
            ],
            \"resource_requests\": {
                \"DISK_GB\": 35,
                \"MEMORY_MB\": 1000,
                \"VCPU\": 4
            }
        }
    }" \
    https://$SITE/consumer/)

if [ "$RESPONSE" -eq 204 ]; then
		exit 0
	else
		echo "Error: Expected HTTP status code 204, but got $status"
		exit 1
	fi

echo "All tests completed."
