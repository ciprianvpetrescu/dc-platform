# dc-platform

A three-node bare-metal virtualisation platform, described entirely as code:
Proxmox VE for compute, Ceph for distributed storage, Ansible for configuration,
Terraform for provisioning, and a Prometheus/Grafana stack that watches the
whole thing.

Every node is rebuilt from this repository. There is no undocumented state on
any host, and there are no manual steps.

## The interesting part

The configuration management actually runs - against three systemd containers
that stand in for the nodes. That means the playbooks are **executed and
asserted on** in CI, not just included as text.

```
$ make sim-up && make converge && make test
...
all 25 checks passed
```

What that does and does not cover is written down plainly in
[docs/SIMULATION.md](docs/SIMULATION.md). Proxmox and the Ceph daemons cannot
be installed in a container; those steps are skipped there and marked as such,
rather than hidden behind a `failed_when: false` that would make the test lie.

## Repository layout

```
ansible/
  inventory/       three nodes, management network only
  roles/
    common/        packages, NTP, SSH hardening
    network/       bond, VLANs, storage VLAN with jumbo frames
    proxmox/       PVE install, cluster create and join
    ceph/          monitors, OSDs, pool creation
    monitoring/    Prometheus, Alertmanager, Grafana, Loki
  site.yml         the full build, in dependency order
terraform/         workload VMs, cloned from a template
prometheus/        alert rules - every one names a runbook
runbooks/          ten failure procedures, one per alert
dashboards/        Grafana dashboards as provisioned JSON
sim/               the three-node container simulation
tests/             the suite that runs against it
docs/              architecture, capacity, operations, bootstrap
```

## Design decisions worth reading

**Three monitors, not one.** With three, losing one node keeps quorum. With two,
losing either halts the cluster entirely - a two-node Ceph cluster is a cluster
that is permanently one failure from being down.

**Storage on its own VLAN.** Ceph replication is chatty and latency-sensitive.
Sharing a broadcast domain with guest traffic is the most common cause of a slow
cluster, and it is a decision that is very hard to reverse later.

**Replication factor 3, correctly costed.** Three copies across three disks is
one disk of usable space. The arithmetic - including what happens when a second
failure arrives while the first is still unrepaired - is worked through in
[docs/CAPACITY.md](docs/CAPACITY.md).

**Alerts without runbooks are not shipped.** A test fails if an alert names a
runbook that does not exist, or if a runbook is missing its impact, diagnosis or
recovery section. `prometheus/alerts.yml` and `runbooks/` cannot drift apart.

**Honest service levels.** 99.5% monthly is about three and a half hours of
downtime. That is what this hardware genuinely supports; four nines would be a
target nobody could meet.

## Quick start

```bash
make sim-up       # three simulated nodes
make ssh-config   # throwaway ssh config
make converge     # apply the platform configuration
make test         # 25 checks against the result
make sim-down     # clean up
```

`make help` lists everything else, including `make check` for a dry run and
`make tf-validate` for the Terraform.

## Documentation

| | |
|---|---|
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Node roles, network plan, storage layout, failure tolerance |
| [CAPACITY](docs/CAPACITY.md) | Replica arithmetic, growth path, performance envelope |
| [OPERATIONS](docs/OPERATIONS.md) | Service levels, daily/weekly/monthly routine, change management |
| [RUNBOOKS](docs/RUNBOOKS.md) | Index of the ten failure procedures |
| [BOOTSTRAP](docs/BOOTSTRAP.md) | Blank disk to cluster member, first node vs the rest |
| [SIMULATION](docs/SIMULATION.md) | What is tested, what is not, and why |

## Requirements

- Ansible 2.15+ with `community.general` and `ansible.posix`
- Terraform 1.6+ (only for workload provisioning)
- Docker with Compose v2 (only for the simulation)
- Three nodes with 2 NVMe devices and 2 NICs each, for real deployment

## Licence

MIT - see [LICENSE](LICENSE).
