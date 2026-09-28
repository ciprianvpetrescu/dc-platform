variable "cluster_name" {
  description = "Name of the Proxmox cluster"
  type        = string
  default     = "dc-cluster"
}

variable "pm_api_url" {
  description = "Proxmox API endpoint"
  type        = string
  default     = "https://10.10.0.11:8006/api2/json"
}

variable "pm_user" {
  description = "Proxmox user, including realm"
  type        = string
  default     = "terraform@pve"
}

variable "pm_password" {
  description = "Proxmox password or API token secret"
  type        = string
  sensitive   = true
}

variable "node_names" {
  description = "Cluster members"
  type        = list(string)
  default     = ["dc-01", "dc-02", "dc-03"]
}

variable "vm_specs" {
  description = "Workload VMs to create"
  type = map(object({
    node      = string
    cores     = number
    memory    = number
    disk_size = number
    vlan      = number
  }))
  default = {
    "app-01" = { node = "dc-01", cores = 4, memory = 8192, disk_size = 60, vlan = 20 }
    "app-02" = { node = "dc-02", cores = 4, memory = 8192, disk_size = 60, vlan = 20 }
    "db-01"  = { node = "dc-03", cores = 8, memory = 16384, disk_size = 200, vlan = 20 }
  }
}

variable "template_name" {
  description = "VM template to clone from"
  type        = string
  default     = "debian-12-cloudinit"
}
