# Runbook: High memory

**Alert:** `HighMemory` - above 90 percent available memory used for 10 minutes
**Severity:** Warning

## Impact

Proxmox will start swapping, then the OOM killer takes the largest process.
That is often a VM, which then looks like a random crash to its owner. Memory
exhaustion causes confusing incidents - act before it reaches 100 percent.

## Diagnose

```bash
free -m
ps aux --sort=-%mem | head -15

# per-VM allocation vs actual
qm list
for v in $(qm list | awk 'NR>1{print $1}'); do
  echo "VM $v: $(qm config $v | grep -E '^memory')"
done
```

Distinguish two situations:

- **Allocated but idle** - VMs are set to 32GB and using 4GB. Fix by enabling
  ballooning, not by adding RAM.
- **Actually consumed** - the guest really is using it. Genuine capacity or a leak.

## Mitigate

**Reboot a ballooning VM is not needed** - set the minimum:

```bash
qm set 100 --balloon 4096
```

That lets Proxmox reclaim memory from the guest when the host needs it, without
a reboot.

**If it is a leak inside a guest**, restart the service, not the VM.

## Recover

Confirm memory has actually been released - do not assume it:

```bash
free -m
```

Available memory should be back above 20 percent of total. If a guest was
restarted to clear a leak, confirm the service came back and that the owner
knows, before closing the alert.

## After

- If ballooning is off across the estate, turn it on. This alert usually means
  it was never enabled.
- Record the real usage figures. Over-allocation is a planning problem; the
  fix is a sizing review, not an emergency.
