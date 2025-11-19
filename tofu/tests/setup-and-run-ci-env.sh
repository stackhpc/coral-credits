#!/bin/bash

set -eu

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

PORT=80
METRICS_PORT=8000
SITE=localhost
# Function to check if port is open
check_port() {
	nc -z localhost $PORT
	return $?
}

# Function to make HTTP request and return status code and content
get_http_response() {
    local endpoint="$1"
    local port="$2"
    local response=$(curl -s -w "\n%{http_code}" "http://$SITE:$port/$endpoint")
    echo "$response"
}

# Function to check HTTP status for _status endpoint
check_http_status() {
    local response=$(get_http_response "_status/" $PORT)
    local status=$(echo "$response" | tail -n1)
    local content=$(echo "$response" | sed '$d')

    if [ "$status" -eq 204 ]; then
        echo "Status check passed. (No content for 204 status)"
        return 0
    else
        echo "Error: Expected HTTP status code 204 for _status, but got $status"
        [ -n "$content" ] && echo "Response content: $content"
        return 1
    fi
}

# Function to check HTTP status for metrics endpoint
check_metrics_status() {
    local response=$(get_http_response "metrics/" $METRICS_PORT)
    local status=$(echo "$response" | tail -n1)
    local content=$(echo "$response" | sed '$d')

    if [ "$status" -eq 200 ]; then
        echo "Metrics retrieved successfully. Content:"
        echo "$content"
        return 0
    else
        echo "Error: Expected HTTP status code 200 for metrics, but got $status"
        [ -n "$content" ] && echo "Response content: $content"
        return 1
    fi
}

# Set variables
CHART_NAME="coral-credits"
RELEASE_NAME=$CHART_NAME
NAMESPACE=$CHART_NAME
TEST_PASSWORD="testpassword"

# Install nginx
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

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
    --set ingress.tls.enabled=false \
    --set monitoring.enabled=false

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
TF_VAR_coral_uri=http://$SITE:$PORT

# Get a token
echo "Getting an auth token:"
TF_VAR_auth_token=$(curl -s -X POST -H "$CONTENT_TYPE" -d \
    "{
        \"username\": \"admin\", 
        \"password\": \"$TEST_PASSWORD\"
    }" \
    ${TF_VAR_coral_uri}/api-token-auth/ | jq -r '.token')
echo "Auth Token: $TF_VAR_auth_token"

python -m venv venv
source venv/bin/active
pip install -r ${SCRIPT_DIR}/../../requirements.txt

pytest ${SCRIPT_DIR}/tofu_tests.py

# Scrape prometheus metrics: 
kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME $METRICS_PORT:$METRICS_PORT &
# Wait for port to be open
echo "Waiting for port $METRICS_PORT to be available..."
for i in {1..30}; do
	if check_port; then
		echo "Port $METRICS_PORT is now open"
		break
	fi
	if [ $i -eq 30 ]; then
		echo "Timeout waiting for port $METRICS_PORT"
		exit 1
	fi
	sleep 1
done

# Check metrics status with retries
echo "Checking Prometheus status..."
for i in {1..10}; do
	if check_metrics_status; then
		echo "Success: HTTP status code is 200."
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
