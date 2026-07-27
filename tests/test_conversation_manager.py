"""Regression tests for the conversation package wiring.

Until this was fixed, `from ai_core.conversation import ConversationManager`
crashed on import (a typo importing a nonexistent DriverAgentFlow class),
and even after that, `ConversationManager()` crashed with a NameError
because conversation_manager.py referenced flow classes it never imported.
These are the two bugs that made the whole conversational feature
unusable — this test exists so that regressions there fail loudly.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_core.conversation import ConversationManager


def test_conversation_manager_constructs_without_llm():
    cm = ConversationManager(llm=None)
    assert cm.llm is None
    assert set(cm.flows) == {
        "install", "repair", "backup", "recovery",
        "diagnose", "antivirus", "network", "driver",
    }


def test_process_user_input_falls_back_to_universal_assistant():
    cm = ConversationManager(llm=None)
    response = asyncio.run(cm.process_user_input("bonjour"))
    assert isinstance(response, str) and response


def test_known_intent_starts_the_matching_flow():
    cm = ConversationManager(llm=None)
    # Accented keyword ("démarre") on purpose: intent matching is substring-based
    # and accent-sensitive, so this exercises the real matching path.
    asyncio.run(cm.process_user_input("mon pc ne démarre plus"))
    assert cm.context.current_flow == "repair"


def test_mentioning_an_os_name_does_not_trigger_install():
    """A message describing symptoms ("my Windows 10 keeps crashing") must not
    be routed to the install flow just because it names an OS — that flow
    ends in erasing the target disk. Only an explicit install verb should."""
    cm = ConversationManager(llm=None)
    asyncio.run(cm.process_user_input(
        "My Windows 10 PC keeps randomly restarting, sometimes with a blue screen."
    ))
    assert cm.context.current_flow != "install"


def test_explicit_install_request_still_triggers_install():
    cm = ConversationManager(llm=None)
    asyncio.run(cm.process_user_input("please install Ubuntu on this PC"))
    assert cm.context.current_flow == "install"
