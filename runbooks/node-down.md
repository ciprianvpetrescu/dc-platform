# Runbook: NodeDown

**Alert:** `NodeDown` - node exporter unreachable for 2 minutes
**Severity:** Critical
**Typical cause:** power loss, NIC failure, kernel panic

## Impact

VMs on the affected node are down. If HA is enabled they restart on a surviving
node within roughly 90 seconds. Ceph stays online as long as 2 of 3 nodes are up.

## First: confirm it is real

Monitoring can lie. Check from a second host before touching anything.

```bash
ping -c 3 10.10.0.11
ssh -o ConnectTimeout=5 ansible@10.10.0.11 true
```

If ping works but SSH does not, this is a software problem - go to *SSH down*.
If neither works, the node is genuinely unreachable.

## Diagnose

1. **Physical or power.** Is the chassis powered? Any console output?
   In a remote datacenter, ask the on-site hands to check before assuming.
2. **Management network.** From the switch, is the port up? Check the bond:
   losing both bond members takes the node off the network while the OS runs on.
3. **Kernel panic.** Attach console (IPMI/iDRAC/Proxmox console) and read the
   screen. A panic on the storage VLAN is common and looks identical to a power cut.

## Mitigate

- **Workloads down:** verify they restarted elsewhere before doing anything else.

```bash
# from a surviving node
pvecm nodes
ha-manager status
```

- **Do not** force-start a VM elsewhere by hand while HA is enabled. HA will
  start it too and you will have two copies of the same disk. If you must take
  over manually, put the VM into maintenance mode first:

```bash
ha-manager set vm:100 --state disabled
```

## Recover

1. Power the node back on, or repair the fault.
2. Let it boot fully and confirm the management address answers.
3. Confirm it rejoined the cluster:

```bash
pvecm nodes          # expected: 3 nodes, all with a green ring id
ceph -s              # expected: no 'mon X down' line
```

4. Check for a stale HA state and clear it if the node was fenced:

```bash
ha-manager status
```

## After

- Record the outage start and end. Power loss counts against the availability
  target; note it or the monthly figure will not reconcile.
- If Ceph rebuilt OSDs, watch it finish (`ceph -s`) rather than declaring victory.
- Open a problem ticket if the root cause is recurring - a node that drops
  twice in a month is a pattern, not an incident.
