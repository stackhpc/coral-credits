# coral-credits

Coral credits is a resource management system that helps build a "coral reef style" fixed capacity cloud, cooperatively sharing community resources through interfaces such as: Azimuth, OpenStack Blazar and Slurm.

You can read more about our plans here:
https://stackhpc.github.io/coral-credits

## Blazar configuration

To use this with Blazar you need to add something like this
into your Blazar configuration:

```
[enforcement]
enabled_filters = ExternalServiceFilter
external_service_bearer_token = <token goes here>
external_service_check_create_endpoint = https://credits.<azimuth_url>/consumer/check-create/
external_service_commit_create_endpoint = https://credits.<azimuth_url>/consumer/create/
external_service_check_update_endpoint = https://credits.<azimuth_url>/consumer/check-update/
external_service_commit_update_endpoint = https://credits.<azimuth_url>/consumer/update/
external_service_on_end_endpoint = https://credits.<azimuth_url>/consumer/on-end/
```

To generate the service bearer token do something
like this:
```
CONTENT_TYPE="Content-Type: application/json"
TEST_PASSWORD=<password>
SITE_URL="https://credits.<azimuth_url>"

TOKEN=$(curl -s -X POST -H "$CONTENT_TYPE" -d \
    "{
        \"username\": \"admin\", 
        \"password\": \"$TEST_PASSWORD\"
    }" \
    $SITE_URL/api-token-auth/ | jq -r '.token')
echo "Auth Token: $TOKEN"
```
