# dc-platform - a three-node virtualisation cluster as code

SHELL := /bin/bash
PYTHON ?= python3
COMPOSE := docker compose -f sim/docker-compose.yml
# Ansible may sit in a project venv (a self-hosted box) or on the system PATH
# (a CI runner). Resolve it rather than assuming one machine's layout.
ifeq ($(shell command -v ansible-playbook 2>/dev/null),)
  ifneq ($(wildcard /opt/venv/bin/ansible-playbook),)
    ANSIBLE_BIN := /opt/venv/bin/ansible-playbook
  else
    ANSIBLE_BIN := ansible-playbook
  endif
else
  ANSIBLE_BIN := $(shell command -v ansible-playbook)
endif
ANSIBLE := $(ANSIBLE_BIN) -i ansible/inventory/hosts.ini
.PHONY: help sim-up sim-down sim-reset ssh-config syntax check test converge clean lint

help:  ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

sim-up:  ## start the three simulated nodes
	$(COMPOSE) up -d --build
	@echo "waiting for ssh to come up..."
	@for i in $$(seq 1 30); do \
		if docker exec dc-01 pgrep -x sshd >/dev/null 2>&1; then echo "ready"; break; fi; \
		sleep 1; \
	done

sim-down:  ## stop the simulated nodes
	$(COMPOSE) down -v

sim-reset: sim-down sim-up  ## rebuild the simulation from scratch

ssh-config:  ## write a throwaway ssh config for the simulation
	@printf '%s\n' \
		'Host dc-01' \
		'  HostName 10.10.0.11' \
		'  User ansible' \
		'  IdentityFile $(PWD)/sim/keys/ansible' \
		'  IdentitiesOnly yes' \
		'  StrictHostKeyChecking no' \
		'  UserKnownHostsFile /dev/null' \
		'Host dc-02' \
		'  HostName 10.10.0.12' \
		'  User ansible' \
		'  IdentityFile $(PWD)/sim/keys/ansible' \
		'  IdentitiesOnly yes' \
		'  StrictHostKeyChecking no' \
		'  UserKnownHostsFile /dev/null' \
		'Host dc-03' \
		'  HostName 10.10.0.13' \
		'  User ansible' \
		'  IdentityFile $(PWD)/sim/keys/ansible' \
		'  IdentitiesOnly yes' \
		'  StrictHostKeyChecking no' \
		'  UserKnownHostsFile /dev/null' \
		> sim/ssh_config
	@echo "wrote sim/ssh_config"

syntax:  ## check all playbooks parse
	$(ANSIBLE) --syntax-check ansible/site.yml

check:  ## dry run - shows what would change, touches nothing
	$(ANSIBLE) ansible/site.yml --check --diff

converge: ssh-config  ## apply the full platform configuration
	ANSIBLE_SSH_ARGS="-F sim/ssh_config" DC_SIMULATE=1 $(ANSIBLE) ansible/site.yml

test:  ## run the full test suite against the simulation
	$(PYTHON) tests/test_playbooks.py

lint:  ## static checks on the ansible content
	ansible-lint ansible/ || true

tf-fmt:  ## format the terraform
	terraform fmt -recursive terraform/

tf-validate:  ## validate the terraform
	cd terraform && terraform init -backend=false && terraform validate

clean: sim-down  ## remove the simulation and its volumes
	@rm -f sim/ssh_config
	@echo cleaned
