# Runbook: Ceph OSD down

**Alert:** `CephOSDsDown` - one or more OSDs not reporting up
**Severity:** Critical

## Impact

With replica size 3, one OSD down leaves 2 copies - data is intact but there is
no spare. **A second concurrent OSD failure becomes a data-loss event.** This is
the highest-priority storage situation short of quorum loss.

## Diagnose

```bash
ceph osd tree
ceph osd stat
ceph health detail
```

Identify whether it is a daemon problem or a hardware problem:

```bash
systemctl status ceph-osd@3
journalctl -u ceph-osd@3 -n 80 --no-pager
smartctl -a /dev/nvme1n1 | head -30
```

- Daemon crashed with a clean SMART report: software or configuration.
- SMART reallocated sectors rising, or `media errors` non-zero: the device is
  dying. Replace it.

## Mitigate

**Do not rush to `ceph osd out`.** That starts a full rebalance, which on a
three-node cluster moves a lot of data and can slow every VM. It is the right
move for a failed disk and the wrong move for a daemon that just needs a kick.

**Try the restart first:**

```bash
systemctl restart ceph-osd@3
sleep 30
ceph osd tree | grep -w 3
```

**If the device has failed:**

```bash
ceph osd out 3
# replace the physical device
ceph osd purge 3 --yes-i-really-mean-it
# then recreate on the new device via ansible:
#   ansible-playbook ansible/site.yml --tags ceph --limit dc-02
```

## Recover

```bash
ceph -s                # expect HEALTH_OK, recovery complete
ceph osd tree          # expect the OSD back up and in
```

## After

- Confirm the new OSD is in the CRUSH map and taking data.
- If a disk failed, check the others: identical devices bought together tend to
  fail in the same window. Run a SMART sweep across all OSDs.
