# Bootstrap

How a node gets from a blank disk to a cluster member. Written out because the
first node needs a different procedure from the rest, and that difference is
easy to get wrong.

## Before any of this

- Two NVMe devices per node, cabled and in the firmware boot order
- Two NICs per node, cabled to separate switches if the budget allows
- Switch ports configured as trunks carrying VLANs 10, 20 and 30
- An `ansible` user with an SSH key on every node

## 1. Install the base OS

Proxmox VE 8 from ISO, on the **second** NVMe. The first stays untouched - it
becomes the Ceph OSD later and anything already on it would be wiped.

At install time:

- Hostname `dc-01`, `dc-02`, `dc-03`
- Management address on VLAN 10 (`10.10.0.11` etc.)
- Root password: set it for the install, then rely on the SSH key

Proxmox's installer writes the second device's partition layout. Confirm which
device is which before starting - getting this backwards destroys the disk you
meant to keep.

## 2. Give Ansible a way in

```bash
ssh-copy-id ansible@10.10.0.11
```

Then confirm the key works, because everything after this depends on it:

```bash
make ssh-config
ansible -i ansible/inventory/hosts.ini all -m ping
```

## 3. Run the playbook

The first node creates the cluster. The others join it. The roles handle the
ordering, but the first run on real hardware should be watched rather than left
unattended:

```bash
ansible-playbook -i ansible/inventory/hosts.ini ansible/site.yml
```

Watch for these, in order:

1. **common** - packages, NTP, SSH hardening. If NTP does not converge, stop:
   Ceph will not form quorum with drifting clocks.
2. **network** - the bond and the VLANs. `serial: 1` means one node at a time, so
   a mistake takes one node off the network rather than all three.
3. **proxmox** - installation, then cluster create on dc-01 and join on the rest.
4. **ceph** - monitors, OSDs, pool.

## 4. Build the VM template

Terraform clones from a template, which is built once by hand:

1. Download a Debian 12 cloud image to `dc-01`.
2. Create a VM (id 9000) from it, add `qemu-guest-agent`, install it, then
   convert to a template.
3. Confirm it is visible on all three nodes - it lives on Ceph, so it should be.

```bash
qm template 9000
```

## 5. Create the workloads

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## 6. Verify

```bash
pvecm nodes          # 3 nodes, all with a ring id
ceph -s              # HEALTH_OK, 3 mons in quorum, 3 OSDs up
ceph osd tree        # one OSD per node, all up and in
ha-manager status    # nothing in an error state
```

Then run the simulation suite once more before declaring done. It is quick, and
it catches the case where the node you just built does not quite match the
three that CI has been testing.
