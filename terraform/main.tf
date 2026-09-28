terraform {
  required_version = ">= 1.6"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.66"
    }
  }
}

provider "proxmox" {
  endpoint = var.pm_api_url
  username = var.pm_user
  password = var.pm_password
  insecure = true # self-signed certificate on the cluster API
}

# The storage pool is created by Ansible before Terraform runs, because the
# Ceph pool has to exist for a VM disk to be placed on it. Terraform only
# references it.
resource "proxmox_virtual_environment_vm" "workload" {
  for_each = var.vm_specs

  name      = each.key
  node_name = each.value.node

  clone {
    vm_id = 9000
    # The template is built once from a cloud image; see docs/BOOTSTRAP.md.
  }

  agent {
    enabled = true
  }

  cpu {
    cores = each.value.cores
    type  = "host"
  }

  memory {
    dedicated = each.value.memory
    floating  = each.value.memory # ballooning enabled
  }

  disk {
    datastore_id = "vmstore" # the Ceph pool
    size         = each.value.disk_size
    interface    = "scsi0"
    file_format  = "raw"
    cache        = "none" # let Ceph do the caching
  }

  network_device {
    bridge  = "vmbr0"
    model   = "virtio"
    vlan_id = each.value.vlan
  }

  initialization {
    type = "nocloud"
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
  }

  lifecycle {
    # Never destroy a workload because a spec changed. Change the spec, then
    # plan the replacement as its own deliberate step.
    prevent_destroy = true
    ignore_changes  = [clone, disk]
  }
}
