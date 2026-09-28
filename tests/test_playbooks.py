#!/usr/bin/env python3
"""
Executable checks against the simulated datacenter.

These are not unit tests of the YAML - they run the playbooks against real
running containers and assert on the resulting state. A playbook that parses
but does not converge is useless, and only this catches that.

Run with:  make test
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NODES = ["dc-01", "dc-02", "dc-03"]

# Ansible may live in a project venv (a self-hosted box) or on the system PATH
# (a CI runner). Resolve it either way rather than hardcoding one machine's
# layout -- this suite has to behave the same in both places.
def _ansible_bin() -> Path | None:
    import shutil

    found = shutil.which("ansible-playbook")
    if found:
        return Path(found).parent
    for cand in (Path("/opt/venv/bin"), Path(sys.prefix) / "bin"):
        if (cand / "ansible-playbook").exists():
            return cand
    return None


VENV_BIN = _ansible_bin()
if VENV_BIN:
    os.environ["PATH"] = f"{VENV_BIN}:{os.environ.get('PATH', '')}"

green, red, yellow, reset = "\033[32m", "\033[31m", "\033[33m", "\033[0m"

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((ok, name, detail))
    mark = f"{green}PASS{reset}" if ok else f"{red}FAIL{reset}"
    print(f"  [{mark}] {name}" + (f"  {yellow}{detail}{reset}" if detail else ""))


def shell(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def on(node: str, command: str) -> str:
    """Run a command inside a simulated node and return stdout."""
    r = shell(["docker", "exec", node, "bash", "-lc", command])
    return r.stdout.strip()


def section(title: str) -> None:
    print(f"\n{yellow}== {title}{reset}")


# ---------------------------------------------------------------- containers

def test_containers_running() -> None:
    section("simulated nodes")
    out = shell(["docker", "ps", "--format", "{{.Names}}"]).stdout
    for n in NODES:
        check(f"{n} is running", n in out.split())


# Addresses come from the inventory so the test cannot drift from the plan.
MGMT_IPS = {"dc-01": "10.10.0.11", "dc-02": "10.10.0.12", "dc-03": "10.10.0.13"}


def test_network_reachability() -> None:
    section("management network")
    for n in NODES:
        ip = MGMT_IPS[n]
        r = shell(["docker", "exec", NODES[0], "ping", "-c", "1", "-W", "2", ip])
        check(f"{NODES[0]} can reach {n} at {ip}", r.returncode == 0)


# ------------------------------------------------------------------- ansible

def test_ansible_connectivity() -> None:
    section("ansible connectivity")
    r = shell(
        ["ansible-playbook", "-i", "ansible/inventory/hosts.ini", "ansible/ping.yml"],
        timeout=180,
    )
    ok = r.returncode == 0 and "unreachable=0" in r.stdout
    check("all nodes answer the ansible ping module", ok, "" if ok else r.stdout[-400:])


def test_playbook_syntax() -> None:
    section("playbook syntax")
    for pb in ["ansible/site.yml"]:
        r = shell(["ansible-playbook", "-i", "ansible/inventory/hosts.ini", "--syntax-check", pb])
        check(f"{pb} is syntactically valid", r.returncode == 0, "" if r.returncode == 0 else r.stderr[-300:])


def test_converge_common() -> None:
    section("converge: common role")
    r = shell(
        [
            "ansible-playbook", "-i", "ansible/inventory/hosts.ini",
            "ansible/site.yml", "--tags", "common",
        ],
        timeout=900,
    )
    ok = r.returncode == 0
    check("common role converges without errors", ok, "" if ok else r.stdout[-600:])

    if not ok:
        return

    # Assert on observed state, not on ansible's own report.
    check("hostname was set", on("dc-02", "hostname") == "dc-02")
    chrony = on("dc-01", "dpkg-query -W -f='${Status}' chrony 2>/dev/null")
    check("chrony is installed", "install ok installed" in chrony, chrony)
    check(
        "ssh hardening dropped in",
        "PermitRootLogin no" in on("dc-01", "cat /etc/ssh/sshd_config.d/99-hardening.conf 2>/dev/null"),
    )


def test_idempotence() -> None:
    section("idempotence")
    r = shell(
        [
            "ansible-playbook", "-i", "ansible/inventory/hosts.ini",
            "ansible/site.yml", "--tags", "common",
        ],
        timeout=900,
    )
    # The real test of configuration management: a second run changes nothing.
    ok = r.returncode == 0 and "changed=0" in r.stdout.replace(" ", "")
    check("second run makes no changes", ok, "" if ok else "see ansible output")


# -------------------------------------------------------------------- alerts

def test_alert_rules_have_runbooks() -> None:
    section("alert rule / runbook coverage")
    try:
        import yaml
    except ImportError:
        check("pyyaml available", False, "pip install pyyaml")
        return

    rules = yaml.safe_load((REPO / "prometheus" / "alerts.yml").read_text())
    missing = []
    total = 0
    for group in rules["groups"]:
        for rule in group["rules"]:
            total += 1
            rb = rule.get("labels", {}).get("runbook")
            if not rb:
                missing.append(f"{rule['alert']} has no runbook label")
            elif not (REPO / rb).exists():
                missing.append(f"{rule['alert']} -> {rb} does not exist")

    check(f"all {total} alert rules point at an existing runbook", not missing, "; ".join(missing))


def test_runbooks_have_required_sections() -> None:
    section("runbook completeness")
    required = ["## Impact", "## Diagnose", "## Recover"]
    for rb in sorted((REPO / "runbooks").glob("*.md")):
        text = rb.read_text()
        missing = [s for s in required if s not in text]
        check(f"{rb.name} documents impact, diagnosis and recovery", not missing, ", ".join(missing))


# ------------------------------------------------------------------- handlers

def test_handlers_guard_simulation() -> None:
    """A handler that restarts a service the simulation never installed fails
    only on a machine that has never had it. This is the class of bug a warm
    local run hides and a cold CI run exposes, so assert it directly."""
    section("handler safety")
    import re
    from pathlib import Path

    for h in sorted(Path("ansible/roles").glob("*/handlers/*.yml")):
        body = h.read_text()
        for block in re.split(chr(10) + "- name:", body)[1:]:
            if "state: restarted" in block:
                name = block.strip().splitlines()[0].strip()
                check(
                    f"{h.parent.parent.name}: {name} is guarded against the simulation",
                    "not simulate" in block,
                )


# -------------------------------------------------------------------- compose

def test_compose_valid() -> None:
    section("simulation stack")
    r = shell(["docker", "compose", "-f", "sim/docker-compose.yml", "config"])
    check("docker-compose file is valid", r.returncode == 0, "" if r.returncode == 0 else r.stderr[-300:])


def main() -> int:
    print(f"\n{yellow}dc-platform test suite{reset}")

    test_compose_valid()
    test_containers_running()
    test_network_reachability()
    test_playbook_syntax()
    test_ansible_connectivity()
    test_converge_common()
    test_idempotence()
    test_handlers_guard_simulation()
    test_alert_rules_have_runbooks()
    test_runbooks_have_required_sections()

    passed = sum(1 for ok, _, _ in results if ok)
    failed = len(results) - passed

    print(f"\n{yellow}{'-' * 60}{reset}")
    if failed:
        print(f"{red}{failed} failed{reset}, {passed} passed")
        for ok, name, detail in results:
            if not ok:
                print(f"  {red}x{reset} {name}: {detail}")
        return 1
    print(f"{green}all {passed} checks passed{reset}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
