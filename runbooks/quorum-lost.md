# Runbook: Ceph monitor quorum lost

**Alert:** `CephMonQuorumLost` - `ceph_mon_quorum_status == 0`
**Severity:** Critical
**Typical cause:** two of three monitors unreachable, or clock drift

## Impact

- **Writes have stopped cluster-wide.** Every VM with a Ceph-backed disk will
  hang on write, then recover when quorum returns. Do not reboot those VMs.
- **Reads may still work.** RBD reads do not need quorum; processes that only
  read carry on. This is why the alert is critical but not immediately fatal.

## Diagnose

From any reachable monitor:

```bash
ceph mon stat
ceph -s
systemctl status ceph-mon@$(hostname)
```

`ceph mon stat` prints the current epoch and the running monitor set. If it
lists fewer monitors than expected, identify which are missing.

Check for clock drift - Ceph refuses quorum when clocks differ by more than
about 0.05s:

```bash
chronyc tracking
```

A `System time` offset above a few milliseconds is the answer, and the fix is
under *Clock drift* below.

## Mitigate

**Case 1 - one monitor down, two up.** Quorum is intact. This alert should not
be firing; if it is, the metric itself is stale. Restart the exporter on the
surviving nodes.

**Case 2 - two down, one up.** Quorum is genuinely lost. Restore one:

```bash
# on the affected monitor
systemctl restart ceph-mon@dc-02
journalctl -u ceph-mon@dc-02 -n 50 --no-pager
```

**Case 3 - all three down.** Restart them starting with the one that holds the
most recent data. Find it by comparing the epoch in each monitor's store.

**Clock drift.** Correct time first, then quorum returns by itself:

```bash
chronyc makestep
sleep 5
ceph mon stat
```

## Recover

Once two monitors agree, quorum forms automatically and writes resume. Confirm:

```bash
ceph -s              # expected: HEALTH_OK or HEALTH_WARN, never MON_DOWN
ceph mon stat
```

VMs that were blocked on write should resume without intervention. If a VM
still hangs, check its disk, not the cluster.

## After

- The window of lost writes matters. Anything written and acknowledged during
  an outage is safe; anything the application held in memory is not. Tell the
  application owner rather than guessing.
- If drift caused it, check NTP reachability on all three nodes - drift on one
  node today is drift on all of them tomorrow.
