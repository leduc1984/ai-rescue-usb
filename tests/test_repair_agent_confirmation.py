"""Tests for the confirm/dry_run gate in agents/repair/repair_agent.py.

This locks in the fix for a bug where ui/server.py's /api/repair endpoint
called auto_repair(dry_run=False, confirm=False), which executes MEDIUM-risk
system commands (e.g. bootrec, BCD rewrite) with no user confirmation at all.
auto_repair itself was correct — confirm=True is meant to gate MEDIUM+ risk
actions — the bug was the caller unconditionally overriding it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.repair.repair_agent import RepairAgent, RepairResult, RiskLevel


def make_stub_agent():
    """A RepairAgent whose execute_repair never touches the real system."""
    agent = RepairAgent()
    agent.executed_actions = []

    def fake_execute(action, dry_run=False):
        agent.executed_actions.append(action.name)
        return RepairResult(action=action.description, success=True, output="", error="", time_taken=0)

    agent.execute_repair = fake_execute
    return agent


def test_medium_risk_actions_are_not_executed_without_confirmation():
    agent = make_stub_agent()
    actions = agent.diagnose("windows", ["boot problem"])
    assert any(a.risk == RiskLevel.MEDIUM for a in actions), "test setup needs a MEDIUM-risk action"

    results = agent.auto_repair("windows", ["boot problem"], dry_run=False, confirm=True)

    medium_names = {a.name for a in actions if a.risk == RiskLevel.MEDIUM}
    assert not (medium_names & set(agent.executed_actions))
    assert any(r.error == "Confirmation requise" for r in results)


def test_medium_risk_actions_execute_once_confirmed():
    agent = make_stub_agent()
    actions = agent.diagnose("windows", ["boot problem"])
    medium_names = {a.name for a in actions if a.risk == RiskLevel.MEDIUM}

    agent.auto_repair("windows", ["boot problem"], dry_run=False, confirm=False)

    assert medium_names.issubset(set(agent.executed_actions))


def test_safe_and_low_risk_actions_always_execute():
    agent = make_stub_agent()
    actions = agent.diagnose("windows", ["boot problem"])
    safe_low_names = {a.name for a in actions if a.risk in (RiskLevel.SAFE, RiskLevel.LOW)}

    agent.auto_repair("windows", ["boot problem"], dry_run=False, confirm=True)

    assert safe_low_names.issubset(set(agent.executed_actions))
