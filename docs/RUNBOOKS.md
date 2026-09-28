# Runbooks

An index. Every alert in `prometheus/alerts.yml` names one of these, and a test
fails if that link ever breaks.

| Runbook | Fires when | Severity |
|---|---|---|
| [node-down](node-down.md) | A node stops reporting | Critical |
| [quorum-lost](quorum-lost.md) | Ceph monitor quorum is lost | Critical |
| [osd-down](osd-down.md) | A Ceph OSD is not up | Critical |
| [ceph-degraded](ceph-degraded.md) | Ceph is `HEALTH_WARN` or `HEALTH_ERR` | Warning / Critical |
| [osd-near-full](osd-near-full.md) | An OSD is below 15% free | Warning |
| [rebalance](rebalance.md) | Recovery still running after 20 min | Informational |
| [high-cpu](high-cpu.md) | CPU over 85% for 15 min | Warning |
| [high-memory](high-memory.md) | Memory over 90% for 10 min | Warning |
| [disk-space](disk-space.md) | A filesystem over 85% | Warning |
| [backup-failed](backup-failed.md) | No backup in 26 hours | Critical |

## The conventions

Every runbook has the same three sections, because at three in the morning the
last thing anyone wants is to read a document to find out where the useful part
is.

- **Impact** - what is broken, what is at risk, and how urgent this actually is.
- **Diagnose** - the commands to run, and what their output means.
- **Recover** - how to confirm it is genuinely fixed.

Most also carry an **After** section: the follow-up that stops it recurring.
The incident is not over when the graph turns green.

## Why these exist

An alert without a runbook is a notification that someone is needed, with no
indication of what for. The runbook is what turns a page into an action.

They are also the reason the alert set is small. Ten alerts with ten accurate
runbooks beats forty alerts where most are ignored - and **an alert that fires
routinely and gets ignored is worse than no alert at all**, because it teaches
everyone to ignore the system.

## Fixing a runbook

Runbooks go stale. Systems change, and commands that used to be correct start
returning errors.

The rule: **if a runbook sends you the wrong way during a real incident, fix it
immediately**, while the details are still fresh. Not in the next review - then.

CI checks that each alert points at an existing runbook and that each runbook
has its three required sections. It cannot check whether the commands are still
correct. Only use does that.
