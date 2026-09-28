# Runbook: Ceph health degraded

**Alerts:** `CephHealthWarn` (`HEALTH_WARN`), `CephHealthCritical` (`HEALTH_ERR`)
**Severity:** Warning for WARN, Critical for ERR

## Impact by state

| State       | Meaning                              | Impact on workloads        |
|-------------|--------------------------------------|----------------------------|
| HEALTH_OK   | normal                               | none                       |
| HEALTH_WARN | redundancy reduced, still serving    | none - fix calmly          |
| HEALTH_ERR  | data at risk, or I/O is blocked      | possible VM hangs          |

## Diagnose

Always start with the detail, never the summary:

```bash
ceph health detail
ceph -s
ceph osd tree
```

`ceph health detail` names the specific condition. The common ones:

- `DEGRADED` - objects below their replica count. A node or OSD is down.
  Redundancy is reduced but data is safe until a second failure. **This is the
  common case and the important one: you now have no margin.**
- `OSD_NEAR_FULL` - an OSD above 85 percent. Go to `osd-near-full.md`.
- `SLOW_OPS` - I/O latency above threshold. Check the storage VLAN first.
- `MON_CLOCK_SKEW` - go to `quorum-lost.md`, clock drift section.
- `PG_AVAILABILITY` - placement groups unavailable. Writes to affected PGs block.

## Mitigate

**DEGRADED with an OSD down:**

```bash
ceph osd tree                       # find the down OSD id
systemctl status ceph-osd@3
journalctl -u ceph-osd@3 -n 50 --no-pager
```

If it is a transient failure, restarting the OSD daemon is enough. If the
device has failed, mark it out and let the cluster rebuild:

```bash
ceph osd out 3        # starts rebalancing
```

**Watch the rebuild - do not walk away:**

```bash
watch -n 10 'ceph -s | head -20'
```

Recovery competes with live traffic. If VM latency climbs, throttle it:

```bash
ceph tell osd.* injectargs '--osd_max_backfills 1'
ceph tell osd.* injectargs '--osd_recovery_max_active 1'
```

Remove the throttle after recovery finishes, or the next rebuild will be slow.

## Recover

```bash
ceph -s              # wait for HEALTH_OK and 'recovery: 0 B/s'
```

## After

- **If it was a disk:** replace it. Rebuild restored redundancy but the capacity
  never came back; the cluster is now under-sized and one more loss hurts more.
- **If it was transient:** find out why before closing. A flapping OSD will do
  this again next month.
- Update the capacity sheet if a device was removed.
