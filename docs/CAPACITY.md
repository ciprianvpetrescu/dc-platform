# Capacity

The arithmetic behind the replica settings, with the failure cases worked
through. Every number here is derived rather than estimated.

## Raw capacity

| | |
|---|---|
| Nodes | 3 |
| OSDs | 1 per node, 960GB usable each |
| Raw | 2,880GB |
| Replication factor | 3 |
| Usable, no failures | 960GB |

**Three copies of everything, from three disks, gives one disk of usable space.**
That is the whole cost of the design, and it is the number to quote when someone
asks why only a third of the bought capacity is available.

## Why not replication factor 2?

A factor of 2 would give 1,440GB usable - half as much again. It was rejected
because a factor of 2 tolerates one failure exactly as well as a factor of 3
does, but no better than that, and it loses the ability to survive a correlated
failure. With 3 copies spread across 3 nodes, a disk that dies while a node is
being rebuilt is survivable. With 2, it is not.

## Failure arithmetic

Notation: `size` is the replica count, `min_size` is the number of copies that
must be writable for I/O to continue.

`size = 3`, `min_size = 2`:

| Nodes up | Copies on disk | Data safe | Writes accepted |
|---|---|---|---|
| 3 | 3 | yes | yes |
| 2 | 2 | yes | yes - **no spare** |
| 1 | 1 | **no** | no |

The 2-node row is the one that matters. Reads and writes continue, so nothing
looks wrong, but there is no longer any redundancy. **A second failure in this
state is data loss.** This is why `NodeDown` is critical rather than warning,
and why the `DEGRADED` state gets fixed promptly rather than left overnight.

## The full-size objection

With `size = 3` on exactly three nodes, a node outage leaves exactly
`min_size`. There is no fourth copy to rebuild from and no room to reconstruct.

The textbook answer is four nodes at `size = 3`: lose one and you still have
three copies spread over three, with the fourth free to receive a rebuild.

This design uses three nodes and accepts the tighter margin, on the reasoning
that a node outage is a **repair event**, not a capacity event - the node comes
back and the rebuild happens then. Where that reasoning breaks down is a
lengthy hardware repair: if a node is off for a week and a second disk fails in
that week, the data is gone.

That is a real risk and it is the reason `osd-down.md` and `ceph-degraded.md`
both say to replace a failed disk promptly rather than scheduling it for later.

## Growth path

| Change | Usable | Survives |
|---|---|---|
| 3 nodes x 1 OSD, size 3 (today) | 960GB | 1 node or 1 OSD |
| 4 nodes x 1 OSD, size 3 | 1,280GB | 1 node, with room to rebuild |
| 3 nodes x 2 OSDs, size 3 | 1,920GB | 2 OSDs, but only if they are on different nodes |

Adding a fourth node is the better move: it buys the rebuild margin as well as
capacity. Adding a second OSD per node to a three-node cluster raises capacity
but not the failure tolerance in the way people expect - losing one node still
removes two OSDs at once.

## Performance envelope

Numbers below are the honest expectation for this hardware, not benchmarks.

| Metric | Expect | Constraint |
|---|---|---|
| Sequential write | 1-2 GB/s | 10GbE storage VLAN |
| Sequential read | 2-3 GB/s | read from any replica |
| Random 4K IOPS | 40-80k | NVMe across 3 nodes |
| Rebuild, one full OSD | 20-40 min | throttled during business hours |

The rebuild figure is the one that matters operationally. During a rebuild the
cluster is both serving live traffic and copying data, which is why the
runbooks throttle recovery rather than letting it saturate the storage VLAN.

## What is not modelled

- **Compression and erasure coding.** Both would change the usable figures
  materially. Neither is enabled, because with a single OSD per node the CPU
  cost is not worth it at this scale.
- **Snapshots.** RBD snapshots share blocks, so their cost is far below their
  apparent size, but they still consume capacity as the source image diverges.
  There is no allowance for them above.
- **The OS disks.** The second NVMe in each node carries the operating system
  and the Ceph journal. That is why it is not an OSD.
