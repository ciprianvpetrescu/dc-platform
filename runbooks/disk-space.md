# Runbook: Disk filling up

**Alert:** `DiskFillingUp` - above 85 percent on a non-ephemeral filesystem
**Severity:** Warning

## Impact

At 100 percent the node stops writing logs, and on Proxmox, `/var/lib/vz`
full means failed backups and failed VM disks. Reaching 100 percent on the OS
disk is one of the few ways to lose a node to something entirely preventable.

## Diagnose

```bash
df -h
du -xhd1 / | sort -h | tail -10
```

On a hypervisor, these are the usual suspects:

- `/var/log` - a log that grew. Find it, fix the cause, truncate the file.
- `/var/lib/vz` - ISO images and templates. Often the real culprit: a few
  6GB installer ISOs nobody remembers downloading.
- `/var/lib/ceph` - OSD data. If it is the OS disk, an OSD was created in the
  wrong place. That needs fixing properly, not deleting.
- Stale VM snapshots - they grow quietly and are easy to forget.

## Mitigate

```bash
# largest files, everywhere
du -ahx / --max-depth=4 | sort -rh | head -25

# old logs
journalctl --vacuum-time=14d
find /var/log -name '*.gz' -mtime +30 -delete

# unused ISOs - check with the team before removing anything
ls -lh /var/lib/vz/template/iso/
```

## Do not

- Delete from `/var/lib/ceph` to make space. You will corrupt an OSD.
- Delete a VM's disk because it is large. Check ownership first.

## Recover

Confirm the filesystem is back below the threshold and that whatever needed
the space can now write:

```bash
df -h
```

If a service was failing because it could not write, restart it rather than
waiting for the next scheduled run - a log daemon that hit ENOSPC will often
stay wedged until it is bounced.

## After

- Truncating a log is a temporary fix. The log grew for a reason - find it, or
  you will be back here in a week.
- Add a retention policy to whatever filled the disk.
