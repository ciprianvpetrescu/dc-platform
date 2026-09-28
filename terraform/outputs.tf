output "vm_ids" {
  description = "Created VM identifiers"
  value       = { for k, v in proxmox_virtual_environment_vm.workload : k => v.vm_id }
}

output "vm_nodes" {
  description = "Which node each VM landed on"
  value       = { for k, v in var.vm_specs : k => v.node }
}
