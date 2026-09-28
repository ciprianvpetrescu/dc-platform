# Runbook: Ceph OSD near full

**Alert:** `CephOSDNearFull` - below 15 percent free on an OSD
**Severity:** Warning

## Impact

Nothing yet - this is a predict-the-failure alert. The impact being prevented:
when any OSD crosses 95 percent, Ceph stops accepting writes **cluster-wide**,
which stops every VM with a Ceph-backed disk, not just the ones on that OSD.
A full OSD is therefore a whole-estate outage, which is why it is caught here at
15 percent free rather than reacted to when it happens.

## Why this matters more than it looks

Ceph stops accepting writes cluster-wide at 95 percent OSD usage, and slows
sharply around 85. One full OSD takes down writes for every VM, not just the
ones on that OSD. This alert fires well before that so it never happens.

## Diagnose

```bash
ceph osd df tree
ceph df detail
ceph osd df | sort -k7 -n | tail -5
```

Look at two numbers: the individual OSD percentage, and the pool percentage.
If one OSD is far above the others, data is unevenly distributed - usually
weighting, sometimes a CRUSH rule.

## Mitigate

**Free space now (least disruptive first):**

1. Remove unused VM disks and orphaned RBD images:

```bash
rbd -p vmstore ls
rbd -p vmstore du
```

2. Delete stale snapshots - check `rbd snap ls` per image.
3. Empty the trash - Ceph keeps deleted images for 24 hours by default.

**Fix the imbalance:**

```bash
ceph osd reweight-by-utilization 110
```

This nudges data off the full OSD onto the emptier ones. It is safe and
reversible; monitor with `ceph -s` while it runs.

## Recover

```bash
ceph osd df | tail -5     # expect all OSDs within a few percent of each other
ceph df detail            # pool usage should sit below 80 percent
```

## After

- If the pool as a whole is above 80 percent, this is a capacity problem. Raising
  the alert threshold would be hiding it; add a node or accept a data-retention
  policy change, and get that decision in writing.
