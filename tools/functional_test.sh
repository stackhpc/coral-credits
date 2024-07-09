#!/bin/bash

set -ex

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Function to check if port is open
check_port() {
    nc -z localhost 8080
    return $?
}

# Function to check HTTP status
check_http_status() {
    local status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/_status/)
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
kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME 8080:8080 &

# Wait for port to be open
echo "Waiting for port 8080 to be available..."
for i in {1..30}; do
    if check_port; then
        echo "Port 8080 is now open"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Timeout waiting for port 8080"
        exit 1
    fi
    sleep 1
done

# Check HTTP status with retries
echo "Checking HTTP status..."
for i in {1..10}; do
    if check_http_status; then
        echo "Success: HTTP status code is 204."
        exit 0
    fi
    echo "Attempt $i failed. Retrying in 3 seconds..."
    sleep 3
done

echo "Failed to get correct HTTP status after 10 attempts"
# Get pod logs on failure

# Construct the selector
SELECTOR="app.kubernetes.io/name=$CHART_NAME,app.kubernetes.io/instance=$RELEASE_NAME"

# Get the pod name
POD_NAME=$(kubectl get pods -n $NAMESPACE -l $SELECTOR -o jsonpath="{.items[0].metadata.name}")

# Get the logs
kubectl logs -n $NAMESPACE $POD_NAME

exit 1

#TODO(tylerchristie) check more things