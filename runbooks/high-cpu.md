# Runbook: High CPU

**Alert:** `HighCPU` - sustained above 85 percent for 15 minutes
**Severity:** Warning

## Impact

None directly. Every VM on the node is competing for the same cores, so the
symptom is latency, not failure. Treat it as a capacity signal, not an outage.

## Diagnose

Per-node first, then per-VM. The host total on its own tells you nothing useful.

```bash
# what is using the host CPU
uptime
pidstat 1 5

# what the VMs are doing
qm list
top -b -n 1 -o %CPU | head -20
```

Then look at the VM directly:

```bash
qm monitor 100
  info cpus
  info status
```

## Common causes, ranked

1. **One runaway VM.** By far the most likely. Confirm with the per-VM view above.
2. **Backup or replication window.** A nightly backup at the same time as a
   replication pass will spike both disk and CPU. Stagger them.
3. **Ceph recovery.** Rebalancing is CPU-hungry. If `ceph -s` shows recovery,
   this is expected and temporary - throttle it if it is hurting VMs.
4. **Genuinely under-provisioned.** Only conclude this after ruling out 1-3.

## Mitigate

- **Runaway VM:** identify the process inside the guest and fix it there. Do not
  cap the VM without telling the owner - you will turn a CPU problem into an
  application failure.
- **Backup clash:** move the schedule. Two VMs backing up at once on a three-node
  cluster is normal; all of them at 02:00 is a self-inflicted incident.

## Recover

There is nothing to revert - the node never stopped serving. Confirm the
condition has cleared before closing the alert:

```bash
uptime
```

The load average should be back near its normal band. If it is not, and no VM
was identified as the cause, keep the incident open and treat it as undiagnosed
rather than resolved.

## After

- If it recurs at the same time daily, it is a schedule problem, not capacity.
- If it recurs randomly, look at the VMs' own monitoring before buying hardware.
