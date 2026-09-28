# Architecture

A three-node bare-metal virtualization platform, fully described as code.

## Design goals

1. **No snowflakes.** Every node is rebuilt from `ansible/` alone. No hand edits,
   no "just this once" commands.
2. **No single point of failure.** The platform tolerates the loss of one node
   with no data loss and no manual intervention.
3. **Observable.** Every failure mode has a metric, an alert and a runbook.

## Node roles

| Node  | Role                        | CPU | RAM  | Disk          |
|-------|-----------------------------|-----|------|---------------|
| dc-01 | hypervisor + ceph-mon + mgr | 8   | 32GB | 2x960GB NVMe  |
| dc-02 | hypervisor + ceph-mon       | 8   | 32GB | 2x960GB NVMe  |
| dc-03 | hypervisor + ceph-mon       | 8   | 32GB | 2x960GB NVMe  |

Three monitors is the minimum for Ceph quorum: with three, one node may be lost
and the cluster keeps a majority (2 of 3). With two, losing either node halts
the cluster entirely - that is why this design does not use two.

## Network plan

| VLAN | Purpose        | Subnet         | Notes                              |
|------|----------------|----------------|------------------------------------|
| 10   | Management     | 10.10.0.0/24   | Ansible, monitoring, console access |
| 20   | VM traffic     | 10.20.0.0/24   | Guest workloads                    |
| 30   | Storage (Ceph) | 10.30.0.0/24   | 10GbE, jumbo frames                |

Storage is on its own VLAN deliberately. Ceph replication is chatty and
latency-sensitive; sharing a broadcast domain with guest traffic is the single
most common cause of a slow cluster.

## Storage layout

- Each node contributes one NVMe device as an OSD (object storage daemon).
- Replication factor 3, minimum size 2: every object exists on all three nodes,
  and writes succeed as long as two are reachable.
- The second NVMe on each node carries the OS and the Ceph journals.

The obvious objection is that with size 3 on exactly three nodes, losing one
node leaves exactly the minimum of 2 - there is no spare copy to rebuild from
while the node is down. The alternative is to add a fourth node and keep size 3,
which leaves room to rebuild. This design accepts the tighter margin because a
node outage is treated as temporary (repair and rejoin), not as a capacity
change. The full arithmetic, including what happens if a second node fails while
the first is still down, is in docs/CAPACITY.md.

## Software stack

- **Proxmox VE 8** - virtualization (KVM) and container runtime (LXC)
- **Ceph Reef** - distributed storage
- **Ansible** - configuration management
- **Terraform** - node and VM provisioning
- **Prometheus + Alertmanager + Grafana** - metrics and alerting
- **Loki** - log aggregation

## Failure tolerance

| Failure                | Expected behaviour                                  |
|------------------------|-----------------------------------------------------|
| One node loses power   | VMs restart elsewhere in ~90s, storage stays online |
| One OSD fails          | Cluster degrades, rebalances to 3x over ~20 min     |
| One network link fails | Traffic fails over to the bond partner, no downtime |
| Ceph monitor loss (1)  | Quorum held, no impact                              |
| Ceph monitor loss (2)  | Quorum lost, writes stop, reads continue            |

Each row has a corresponding runbook in `runbooks/`.
