"""Tests for the risk-evaluation logic in security/security_manager.py.

This is the part of the codebase that decides whether a command needs
explicit user confirmation before running, so it's the one place that
most needs automated coverage.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from security.security_manager import Operation, OperationRisk, SecurityManager


def make_op(command: str, **kwargs) -> Operation:
    return Operation(name="test", description="test op", command=command, **kwargs)


def test_read_only_commands_are_safe():
    sm = SecurityManager()
    for cmd in ["lsblk", "lspci", "smartctl -a /dev/sda", "fdisk -l"]:
        assert sm.evaluate_risk(make_op(cmd)) == OperationRisk.SAFE


def test_destructive_commands_are_flagged():
    sm = SecurityManager()
    for cmd in ["mkfs.ext4 /dev/sda1", "dd if=/dev/zero of=/dev/sda", "wipefs /dev/sda"]:
        assert sm.evaluate_risk(make_op(cmd)) == OperationRisk.DESTRUCTIVE


def test_partition_commands_are_high_risk():
    sm = SecurityManager()
    assert sm.evaluate_risk(make_op("parted /dev/sda mkpart")) == OperationRisk.HIGH


def test_boot_commands_are_medium_risk():
    sm = SecurityManager()
    assert sm.evaluate_risk(make_op("grub-install /dev/sda")) == OperationRisk.MEDIUM


def test_destructive_operations_require_confirmation():
    sm = SecurityManager()
    op = make_op("mkfs.ext4 /dev/sda1", affected_disks=["/dev/sda"])
    assert sm.needs_confirmation(op) is True


def test_safe_operations_never_require_confirmation():
    sm = SecurityManager()
    op = make_op("lsblk")
    assert sm.needs_confirmation(op) is False


def test_confirmed_operation_is_not_asked_again():
    sm = SecurityManager()
    op = make_op("grub-install /dev/sda")
    assert sm.needs_confirmation(op) is True
    sm.confirm(op)
    assert sm.needs_confirmation(op) is False
