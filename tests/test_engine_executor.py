"""Regression test for ai_core/engine.py's Executor confirmation gate.

Action.requires_confirmation was declared on every MEDIUM+ risk action
(bootrec, grub-install, ...) but never actually checked anywhere — so
AIRescueCore.process(), reachable via `ai-rescue talk` and
ai_core/main.py's interactive mode, executed real destructive-ish shell
commands with zero confirmation. This locks in the fix.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_core.engine import Executor, Action, ActionType, RiskLevel


def test_medium_risk_action_is_not_executed_by_default():
    executor = Executor()
    action = Action(
        type=ActionType.REPAIR, description="fix boot", command="echo should-not-run",
        risk=RiskLevel.MEDIUM, requires_confirmation=True,
    )
    result = asyncio.run(executor.execute(action))
    assert result["success"] is False
    assert result.get("requires_confirmation") is True


def test_medium_risk_action_executes_once_confirmed():
    executor = Executor()
    action = Action(
        type=ActionType.REPAIR, description="fix boot", command="echo ran",
        risk=RiskLevel.MEDIUM, requires_confirmation=True,
    )
    result = asyncio.run(executor.execute(action, confirm=False))
    assert result["success"] is True


def test_safe_action_always_executes_and_reports_its_description():
    executor = Executor()
    action = Action(type=ActionType.DETECT_HARDWARE, description="detect hw", risk=RiskLevel.SAFE)
    result = asyncio.run(executor.execute(action))
    assert result["success"] is True
    assert result["action"] == "detect hw"
