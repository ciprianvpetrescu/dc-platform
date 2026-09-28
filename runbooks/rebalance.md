# Runbook: Ceph recovery running long

**Alert:** `CephRebalanceRunning` - recovery still active after 20 minutes
**Severity:** Informational

## Impact

None by design - recovery is the cluster healing itself. The impact being
watched for is indirect: recovery consumes disk bandwidth, so VM disk latency
can rise while it runs. A long recovery is also a signal - it means a lot of
data moved, which means a node or OSD was out for a significant period.

## What is happening

After a node or OSD returns, Ceph copies data to restore the replica count. This
is normal and expected. The alert exists because long recovery events impact VM
performance and sometimes hide a deeper problem.

## Diagnose

```bash
ceph -s
ceph osd df tree
ceph pg stat
```

Read the recovery rate and the estimated time remaining from `ceph -s`. Then ask
two questions:

1. **Is it progressing?** Take two readings five minutes apart. A moving byte
   count is healthy. A stuck one is not - check for a flapping OSD.
2. **Is it impacting VMs?** Look at VM disk latency in Grafana. If it is fine,
   leave it alone.

## When to intervene

Only throttle, never stop:

```bash
ceph tell osd.* injectargs '--osd_max_backfills 1'
ceph tell osd.* injectargs '--osd_recovery_max_active 1'
```

Expected duration scales with the data volume - a full 960GB NVMe on a three
node cluster takes tens of minutes, not seconds. That is normal.

## Recover

Recovery ends on its own:

```bash
ceph -s        # 'recovery: 0 B/s' and no active backfills
```

## After

- Remove any throttle you applied, or the next rebuild will crawl.
- If recovery restarted on its own, something is flapping. Find it: a repeating
  recovery is a repeating fault.
