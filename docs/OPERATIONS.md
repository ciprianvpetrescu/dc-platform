# Operations

How this platform is actually run day to day. The runbooks cover failures; this
covers the routine.

## Service levels

Deliberately modest and stated in terms that can be measured.

| | Target | Measured by |
|---|---|---|
| Availability | 99.5% monthly | `up{job="node"}` history |
| Recovery time, single node | 90 seconds | HA restart timestamp to VM up |
| Recovery point | 24 hours | last successful backup |
| Alert acknowledgement | 15 minutes | Alertmanager acknowledgement |

99.5% is about three and a half hours of downtime a month. It is not a boast -
it is what three nodes and one OSD each genuinely supports. A four nines
target on this hardware would be a lie that nobody could meet.

## Daily

Automated. Anything that needs a human every day will not happen on a bad day.

- Alertmanager pages on critical conditions only.
- Backup verification job runs after the nightly backup.
- SMART short test on every OSD.

## Weekly

- Review the alerts that fired. For each: was the runbook accurate? If a runbook
  sent you the wrong way, **fix the runbook now** - not next week, when the
  details are gone.
- Check Ceph pool usage against the growth trend.
- Confirm the last restore test date is under a month old.

## Monthly

- **Restore test.** Restore a backup to a scratch VM and boot it. A backup that
  has never been restored is a hope.
- Patch cycle: apply the unattended upgrades, then plan the Proxmox and Ceph
  upgrades separately. Never upgrade both at once.
- Review capacity against `CAPACITY.md` and update the arithmetic if it changed.

## Quarterly

- Failover drill: power off a node during business hours and confirm HA behaves.
  Do it deliberately, when someone is watching, rather than discovering the
  behaviour during a real outage.
- Full rebuild of one node from Ansible alone, to prove there are no snowflakes.
- Review the alert thresholds. An alert that fires routinely and is ignored is
  worse than no alert.

## Change management

Every change is a pull request against this repository. Specifically:

- No manual edits on a node. If it is not in the repository, it does not exist
  and it will vanish on the next rebuild.
- Playbook changes run in CI against the simulation before they touch hardware.
- A change to `ceph_replica_size` or `ceph_replica_min_size` is a change to the
  failure model. It needs the arithmetic in `CAPACITY.md` updated in the same
  pull request.

## Escalation

| Condition | Who |
|---|---|
| Any critical alert | on-call engineer |
| Quorum lost, or `HEALTH_ERR` | platform lead, immediately |
| Data loss suspected | stop and escalate - do not attempt recovery alone |

## Handover notes

Written for whoever picks this up next:

- The cluster is built entirely from this repository. There is no undocumented
  state on any node.
- The three things most likely to be wrong are clock drift, the storage VLAN and
  full disks. Check those first, in that order.
- Every alert has a runbook. If one is missing or wrong, that is a bug, and the
  test suite treats it as one.
