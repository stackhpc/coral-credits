#!/bin/bash

set -ex

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Install the CaaS operator from the chart we are about to ship
# Make sure to use the images that we just built
helm upgrade coral-credits ./charts \
  --dependency-update \
  --namespace coral-credits \
  --create-namespace \
  --install \
  --wait \
  --timeout 10m \
  --set-string image.tag=${GITHUB_SHA::7} \

