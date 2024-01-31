# Coral Credits Mission

Coral Credits aims to support the building of a "coral reef style" fixed capacity cloud.
A Coral reef style cloud involves cooperatively sharing resources
to maximise your investiment in both people and cloud resources.

Coral credits are focused on how to support sharing of resources
using multiple interfaces such as:
Azimuth, OpenStack Blazar and Slurm

## User Experience

### On-boarding Accounts, Projects and Users

We are assuming clouds are trying to follow the
[AARC blueprint](https://aarc-project.eu/architecture/),
such that user groups are managed via a central AAAI proxy,
typically based on [Indigo IAM](https://indigo-iam.github.io/)
or [Keycloak](https://www.keycloak.org/).

Typically this means the project lead (or principal investigator)
is responsible for ensuring the membership of the groups they
manage in the central AAAI proxy is correct.

Coral Credit Accounts are assocaited to a particular group
defined in the central AAAI proxy. This group typically
has access to many different resource providers.

### Resource Class and Resource Class Hours

A coral credits operator is responsible for defining
the list of available resource classes.
We will use the definition of resource classes used by OpenStack
and defined in the python library
[os-resource-classes](https://docs.openstack.org/os-resource-classes/latest/)

### Allocating credits to Accounts

A federation manager is typically responsible to updating the
allocation of resource credits given to each account.

A credit allocation has the following properties:

* a single account it is associated with
* a start date and an end date
* a resource class
* an integer amount of resource class hours
* list of resource providers where you can consume these credits

To simplify the initial implementation
no account can have overlapping credits
for the same resource class at the
same resource provider,
although existing allocation can be increased
or decresed at any time.
The hope is to add this support in a future,
under the assumption any resource consumption
is only from a single credit pool.

### Resource Providers

There are places where an account gets to
consume their allocated credits.

Coral credits operator is responsible for
onboarding a particular resource provider
and giving them a token to access the
resource consumption API.

### Resource Consumption Requests

Cloud credits are consumed at a specfiic Resource
Provider. The units are resource class hours.

Resource providers should create an appropriate
resource consumption request, before allowing
resources to be consumed.
Only if enough credits are availabe for the
duration of the request will the request be
accepted by the coral credit system.

A resource consumtion request has the following properties:

* account
* user requesting the resource
* resource footprint,
  i.e. a list of resource class and float amounts
* proposed start date
* optionally a proposed end date, if ommitted
  we return when whatever date is first, when
  all credits are used or when all credits have
  expired

#### Example: Azimuth platform

TODO

#### Example: OpenStack Blazar reservation

TODO

#### Example: Slurm job credits

TODO

#### Example: Slurm reservations

TODO
