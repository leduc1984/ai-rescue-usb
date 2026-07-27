"""Tests for ai_core/tool_agent.py — the LLM-driven tool-calling layer.

The LLM itself is mocked (no llama-cpp-python / model file dependency) so
these run in the base test suite. What's being verified is the routing
and safety logic: tool selection falls back to "chat" on any ambiguity,
tools actually call through to real detector/agent objects (mocked here),
and the module never touches anything destructive — it only reads.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_core.tool_agent import ToolAgent, TOOLS


def make_llm(tool_json="{}", summary="ok"):
    llm = MagicMock()
    llm.loaded = True
    llm.model.create_chat_completion.return_value = {
        "choices": [{"message": {"content": tool_json}}]
    }
    llm.generate.return_value = summary
    return llm


def test_select_tool_returns_valid_choice():
    llm = make_llm(tool_json='{"tool": "detect_hardware"}')
    agent = ToolAgent(llm)
    assert agent.select_tool("what's my cpu") == "detect_hardware"


def test_select_tool_rejects_unknown_tool_name():
    llm = make_llm(tool_json='{"tool": "delete_everything"}')
    agent = ToolAgent(llm)
    assert agent.select_tool("do something") == "chat"


def test_select_tool_falls_back_to_chat_on_malformed_json():
    llm = make_llm(tool_json="not json at all")
    agent = ToolAgent(llm)
    assert agent.select_tool("anything") == "chat"


def test_answer_returns_none_when_llm_not_loaded():
    llm = MagicMock()
    llm.loaded = False
    agent = ToolAgent(llm)
    assert agent.answer("what's my cpu") is None


def test_answer_returns_none_for_chat_tool():
    llm = make_llm(tool_json='{"tool": "chat"}')
    agent = ToolAgent(llm)
    assert agent.answer("just chatting") is None


def test_detect_hardware_tool_calls_real_detector_and_summarizes_real_data():
    llm = make_llm(tool_json='{"tool": "detect_hardware"}', summary="Your CPU is FakeCPU-9000.")
    agent = ToolAgent(llm)

    fake_hw = MagicMock()
    fake_hw.cpu.model = "FakeCPU-9000"
    fake_hw.cpu.cores = 8
    fake_hw.cpu.threads = 16
    fake_hw.ram.total_mb = 16384
    fake_hw.disks = []
    fake_hw.bios_type = "uefi"
    fake_hw.secure_boot = True
    agent._hw_detector = MagicMock()
    agent._hw_detector.detect_all.return_value = fake_hw
    agent._load_agents = lambda: None  # don't overwrite our fake

    result = agent.answer("what's my cpu")
    assert result == "Your CPU is FakeCPU-9000."
    # The prompt sent to the LLM must contain the real detected value —
    # this is what makes it "real" tool use instead of the LLM inventing data.
    prompt_sent = llm.generate.call_args[0][0]
    assert "FakeCPU-9000" in prompt_sent


def test_no_tool_reaches_execute_repair_or_install():
    """Sanity check on the registry itself: nothing destructive is exposed."""
    destructive_words = ("repair", "install", "format", "delete", "backup", "recover")
    for name in TOOLS:
        assert name in ("detect_hardware", "detect_os", "diagnose", "list_compatible_os", "chat")
        assert not any(w in name for w in ("format", "delete", "erase"))
