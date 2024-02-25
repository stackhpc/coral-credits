# Coral Credits Mission

Coral Credits aims to support the building of a "coral reef style" fixed capacity cloud.
A Coral reef style cloud involves cooperatively sharing resources
to maximise your investiment in both people and cloud resources.

Coral credits are focused on how to support sharing of
resources from a federated e-infrastructure (or community cloud)
where resources are consumed via multiple interfaces such as:
Azimuth, OpenStack Blazar and Slurm

## On-boarding Accounts, Projects and Users

We are assuming clouds are trying to follow the
[AARC blueprint](https://aarc-project.eu/architecture/),
such that user groups are managed via a central AAAI proxy,
typically based on [Indigo IAM](https://indigo-iam.github.io/)
or [Keycloak](https://www.keycloak.org/).

Typically this means the project lead (or principal investigator)
is responsible for ensuring the membership of the groups they
manage in the central AAAI proxy are correct.

Coral Credit Accounts are assocaited to an account,
and access to that account is limited to a group
defined in the central AAAI proxy. This group typically
has access to many different resource providers,
and often uses more than one interface to access those resources.

## Resource Class and Resource Class Hours

The coral credits operators are responsible for defining
the list of available resource classes.
We will use the definition of resource classes used by OpenStack
and defined in the python library
[os-resource-classes](https://docs.openstack.org/os-resource-classes/latest/)

### Allocating credits to Accounts

A federation manager is typically responsible for updating the
allocation of resource credits given to each account.

A credit allocation has the following properties:

* a single account it is associated with
* a start date and an end date
* credits are a dict of resource class to resource class hours
* list of one or more resource providers
  where you can consume these credits,
  with the default being any resource provider

To simplify the initial implementation
no account can have overlapping credits
valid for the same resource provider,
although an existing allocation can be increased
or decresed at any time.
The hope is to add this support in a future,
under the assumption any resource consumption
is only from a single credit pool.

## Resource Providers

There are places where an account gets to
consume their allocated credits.

Coral credits operator is responsible for
onboarding a particular resource provider
and giving them a token to access the
resource consumption API.

## Resource Consumption Request

Cloud credits are consumed at a specfiic Resource
Provider. The units are resource class hours.
The Resource Provider has to map their local view
of an account and user into how Coral Cloud Credits
views that account. Note this means the user reference
given is likely specific to each resource provider,
although the recomendation will be to use an email
address, to make differences between resource providers
less likely.

Resource providers should create an appropriate
resource consumption request, before allowing
resources to be consumed.
Only if enough credits are availabe for the
duration of the request will the request be
accepted by the coral credit system.

A resource consumtion request has the following properties:

* account
* resources provider
* resources consumption interface
  (e.g. Blazar or Azimuth or Slurm)
* email address of user requesting the resource
* resource footprint,
  i.e. a list of resource class and float amounts
* proposed start date
* optionally a proposed end date, if ommitted
  we return when whatever date is first, when
  all credits are used or when all credits have
  expired

### Example: Azimuth short lived platform

Azimuth plaforms are now forced to pick an end date,
such that we can make a credit consumption request
for a platform we are about to create.

If there are not enough credits, it will be clear
what credits are required to create the platform,
possbily including which platforms could be
stopped early to free up credits for the requested
platform.

When a platform is stopped before the originially
agreed time, the consmption record should be
updated with the new end date, returning the credits
back to the user.

### Example: Azimuth long lived platform

Where platforms are long lived, the scheduled end
date need to be either when their current credits
expire, or possibly sooner if the proposed
platform will consume all reminaing credits before
those credits expire.

Users need to be warned when platforms are about
to be automatically deleted, so they can get
additional credits allocated.

When credits are allocated "back to back" with no
gap, the user is able to request a change to the
end date for the existing credit consumption
request, and with the option to extend to the
maximun date allowed given the current credit
allocation for the associated account.

### Example: Azimuth variable resource usage

All the platforms so far have assumed a uniform
resource usage throught the lifetime of the
platform.

While not supported in the initial implemention,
we need to support the a variety of increases
and decreases in resource during the lifetime
of the cluster.
We likely need to have the option for resource
consumption requests resource footprint
records to have a start and end date that is
indepent of the overall resource consumption
request.

### Example: OpenStack Blazar reservation

This is very similar to the Azimuth case,
except its for an arbitry reservation via
the Blazar API.

To help reservations line up nicely,
and reduce resource fragmentation,
we could enforce that we round up credits
to the nearer time window (e.g. 1 hour,
or one of three 8hr working day windows
each day).

### Example: Many OpenStack projects, one account

It is common to have one project be given separate
openstack projects for Dev/Test, Staging and Production.
In this case, it would be good if they all share a single
credit account, although its clear they which openstack
project is consuming the resources.

### Example: Slurm batch job credits

You could have a single pool of credits,
where you could self-service request that
a some amount of Coral Credits are given to
your Slurm account, such that you can submit
some jobs to your chosen Slurm cluster.

For example, you could reserve 30 days of 1k CPU hours
with a Slurm cluster, and if accepted those
cloud credits are consumed from the central pool.
If that Slurm cluster is very busy, it might not
have any available for your selected 30 day period,
but there might some available next month.
With the idea that a specific federation only has
a limited number of CPU hours available each month
from that Slurm system, and users reserve some of
those, on-demand, when they need need them,
and they have not spent them on other cloud credits.

Its possible that very large credit delegations
to a slurm cluster could be used to expand the slurm
cluster using available cloud resources, depending
on them being from a shared pool of resources,
such as a single OpenStack Ironic based cloud.

### Example: Slurm reservations

Similar to Blazar, you could imagine building the
option to self service Slurm reservations against
a shared resource pool.

### Example: Onboarding to Public Cloud

Without care people can run up unexpected
cloud bills. Automation to convert account
credits into a public cloud account,
correctly setup with spend limits,
bringing the pre-paid credit system to
public clouds.

With all transfer of credits, care must
be taken to ensure unused credits are
refundable when possible, such as public
cloud spend (where possible) is capped
rather than pre-paid as such. Work is
needed to understand how this works
with JISC OCRE:
https://www.jisc.ac.uk/ocre-cloud-framework

### Example: Shared Job Queue (idea)

There are various systems that could create a
job queue that spans multiple resource providers
(or in some cases a common interface at multiple
providers):

* https://armadaproject.io/
* https://dirac.readthedocs.io/en/latest/index.html
* https://kueue.sigs.k8s.io/
* https://github.com/elixir-cloud-aai/cwl-WES
* https://nextflow.io/

Cloud credit users could be consuming cloud credits
when they submit large groups or jobs, (or maybe the
user trades in cloud credits for some credits on the
shared job queue).

Some "free" or "cheaper" queues could exist
for preemtable jobs, that could help consume
the free capacity that exists between cloud
reservations.

### Example: Juypter Hub (idea)

When a user logs into jupyer hub, and their container
is spun up, maybe this could be blocked (using a custom
Authorization plugin or jupyterhub-singleuser wrapper)
if the user doesn't have any credits left,
along side matching configuration in the idle-culling system.

### Example: Seedcorn allocation

One thing not possible with quota, is being
able to hand out a very small amount of resoruce
for people to try things out. You could say
all members of an instituiton automatically get
a seedcorn allocation they could use.
This could become a default allocation amount
for any automatically created accounts.

## Audit logs

All changes should be recorded in an audit log,
that can be quiried via the API

## Visibility for Account holders

There should be a clear view of:

* all active resource allocations for the account
* all consumers associated with each resource allocation,
  so its clear how the credits are being consumed
* A prediction of how many credits will be left
  at the end of the allocation

## Prometheus metrics for operators

Various stats should be made availabe via a prometheus
metrics endpoint, including these per account metrics:

* size of current allocated credits
* size of any not current credits
* remining amount for current active credit allocations
* any active resource consumption records,
  including user and account details

## Periodic reconciliation

Each resource provider is responsble for regularly checking
if there is any drift between the current resource consumption
requests, and the current state of resoruce consumption records.
Only the service knows how to map the records in coral credits
back to the real resources in that service.

## No tracking of usage or efficiency

Coral credits on credit allocations and consumption records
per account, not the current usage in each service.
Coral credis does not track if the resources are being fully
utilized (e.g. job efficieny).

## Policy

Resource Providers, combined with their use of the central
AAI proxy, must ensure users have accepted all policies
before requesting a resource.

The Coral Cloud credits admin must ensure the account PI
has accepted all the policies for the duration of any
credit allocation to thier account.
