# coral_uri = "http://credits.apps.<azimuth-domain>"
# auth_token = Get bearer token with `curl -X POST -H "Content-Type: application/json" -d \
#    "{
#        \"username\": \"admin\", 
#        \"password\": \"$TEST_PASSWORD\"
#    }" \ http://credits.apps.<azimuth-domain>/api_auth_token/

resource_provider_name     = "Test Provider"
resource_provider_email    = "testprovider@example.com"
resource_provider_info_url = "https://www.google.com"

accounts = [
  {
    name                 = "TestAccount1"
    email                = "testaccount1@example.com"
    openstack_project_id = "c2eced313b324cdb8e670e6e30bf387d"
  },
  {
    name                 = "TestAccount2"
    email                = "testaccount2@example.com"
    openstack_project_id = "2fbf511968aa443e883a82283b0f0160"
  }
]

allocations = {
  Q1 = {
    start_date = "2025-09-01-12:00:00"
    end_date   = "2025-12-01-12:00:00"
    projects = [
      {
        account_email = "testaccount1@example.com"
        resources = {
          VCPU    = 40000
          MEMORY_MB  = 4423680
          DISK_GB = 108000
        }
      },
      {
        account_email = "testaccount2@example.com"
        resources = {
          VCPU    = 20000
          MEMORY_MB  = 2000000
          DISK_GB = 200000
        }
      }
    ]
  }
  Q2 = {
    start_date = "2026-01-01-12:00:00"
    end_date   = "2026-04-01-12:00:00"
    projects = [
      {
        account_email = "testaccount1@example.com"
        resources = {
          VCPU    = 80000
          MEMORY_MB  = 8000000
          DISK_GB = 300000
        }
      }
    ]
  }
}
