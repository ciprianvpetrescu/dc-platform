# Simulation

This repository describes a three-node bare-metal cluster. Nobody reviewing it
has three spare servers, which in practice means one of two things happens: the
code is never run, or it is run against something so different that the result
proves nothing.

This project takes a third option. The configuration management is executed for
real against three `systemd` containers that stand in for the nodes.

## What the simulation proves

- Every playbook parses and runs against a live target.
- The roles converge, and a second run is genuinely idempotent.
- The resulting state is asserted on: installed packages, written config files,
  hostnames, file contents.
- Alert rules and runbooks stay in sync - a test fails if an alert mentions a
  runbook that does not exist.

## What it does not prove

Stated plainly, because a test that overstates its coverage is worse than no
test at all.

| Not covered | Why |
|---|---|
| Proxmox VE installation | `pve-manager`'s post-install script writes to `/boot` and needs a real kernel |
| Ceph daemons | `ceph-mon`/`ceph-osd` need a real block device and kernel module loading |
| Kernel module loading | A container shares the host kernel; `modprobe` has nothing to act on |
| Real VLANs and bonding | The containers sit on a Docker bridge, not a trunked switch |
| Storage performance | There is no NVMe, no jitter, no realistic latency |

The roles therefore take a `simulate` flag. Where an operation cannot complete
in a container it is skipped, and the skip is visible in the play recap rather
than hidden behind a `failed_when: false`. Everything else - ordering, file
templating, package installation, service enablement, the cluster create/join
sequence - runs exactly as it would on hardware.

## Running it

```bash
make sim-up      # build and start three nodes
make ssh-config  # write a throwaway ssh config
make converge    # apply the full platform configuration
make test        # run the suite
make sim-down    # tear it all down
```

`make converge` sets `DC_SIMULATE=1`. Running the same playbook without it
targets real hardware and installs Proxmox and Ceph properly.

## Adding a node

Change one line in `ansible/inventory/hosts.ini` and one block in
`sim/docker-compose.yml`. If those two ever disagree, the tests fail - the
management addresses the suite uses are read from the same plan the roles are.

## A note on the ssh configuration

Ansible appends its own `-o` options **after** the ones in
`ansible_ssh_common_args`, and OpenSSH applies options in the order it parses
them. A bare `IdentitiesOnly yes` in the common args is therefore overridden
before Ansible names the key, and authentication silently falls back to the
agent and default keys. The key is specified with
`ansible_ssh_private_key_file` for that reason. This cost an hour to find the
first time; it is written down here so it does not cost another.
