# Runbook: Backup failed

**Alert:** `BackupFailed` - no successful backup in 26 hours
**Severity:** Critical

## Why 26 hours

Backups run nightly. 26 hours means last night was skipped with no room for
slow runs. Two missed nights is a much worse conversation than one, so this
fires early.

## Impact

Recovery point objective is being missed right now. Every hour without a backup
increases what would be lost in a real failure. This is not theoretical - it is
the difference between restoring yesterday and losing a week.

## Diagnose

```bash
systemctl status vzdump
journalctl -u vzdump --since '48 hours ago' --no-pager | tail -50
```

Common causes:

1. **Not enough space** in the backup target. Most common by far.
2. **A VM failed to snapshot** - usually a stuck QEMU process or a full disk.
3. **Backup job disabled** by someone and not re-enabled.
4. **Storage unreachable** - the NFS or Ceph backup target is down.

## Mitigate

```bash
# space check first
ceph df
 df -h /mnt/backup

# clean old backups by retention policy
```

Re-run the failed job manually. Do not wait for the schedule:

```bash
vzdump 100 --storage backup-nfs --mode snapshot --compress zstd
```

## Recover

Confirm a completed backup exists and is readable - an unverified backup is not
a backup:

```bash
ls -lh /mnt/backup/dump/
# restore-test the most recent one to a scratch VM at least monthly
```

## After

- **A backup that has never been restored is a hope, not a backup.** Note the
  date of the last successful restore test. If it is more than a month ago,
  schedule one.
- If space was the cause, get the retention policy agreed rather than deleting
  whatever looks oldest.
