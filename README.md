# 🚀 AI Rescue USB

### **An AI assistant that helps you rescue a broken computer — no technician required.**

> Imagine a world where **anyone** — regardless of technical skill — can rescue a broken computer, recover lost photos, or install a new OS just by talking. That world is AI Rescue USB.

---

## 🌠 The Vision

**Every person on Earth deserves a working computer.**

Yet when a computer breaks, most people are stuck: they don't know how to fix it, they can't afford a technician, and they can't wait days for help. AI Rescue USB changes that.

We believe **computer rescue should be as simple as asking for help**. Plug in a USB, boot it, talk to the AI. Done.

This isn't just software — it's a **first-aid kit for computers** that runs offline and aims to work across most hardware. Our goal is to create an AI assistant that helps people perform computer repairs that traditionally require a technician.

---

## 💥 The Problem We're Solving

- **7+ billion computers worldwide**, most without any built-in recovery
- **$100-500** for a single visit to a repair shop (for a 5-minute fix)
- **3-5 days** average wait for professional help
- **Zero offline recovery** for failing drives
- **Language barrier** for non-English speakers trying CLI tools

Current alternatives (Windows PE, Hiren's, Ultimate Boot CD) require **technical knowledge**, memorizing commands, and navigating menus. Our target — your parents, your grandparents, anyone — can't use them.

---

## ✨ The Solution: Talk to Your AI

**One USB stick. One conversation. One fixed computer.**

```
💬 You: "My Windows won't start, blue screen."
🤖 AI:  I can help. Scanning your system... found corrupted boot files.
         Shall I fix them? (safe operation, won't delete your data)
💬 You: "Yes"
🤖 AI:  ✅ Boot repaired. Restart your computer — it will work now.
```

No terminals. No commands. No jargon. Just conversation.

---

## 🔒 100% Local. Nothing Ever Leaves Your Machine.

The AI in AI Rescue USB runs **entirely on your computer** — no cloud API, no account, no telemetry.

- **The LLM is local.** A quantized model (Llama-3.2-3B or similar, GGUF format) runs on CPU via `llama.cpp`, right there on the USB stick. There's no API key to configure because there's no remote service to call.
- **Your data never gets uploaded.** Diagnostics, file scans, screenshots you show the AI, the contents of your disks — none of it goes anywhere. The tool has no network dependency for its core function; internet is only ever used, optionally, to download an OS installer image.
- **It works with no internet at all.** Unplug the network cable and it still repairs, backs up, and diagnoses — that's the whole point of an offline-first rescue tool.
- **No accounts, no sign-up, no license server.** Boot it and use it.

In an era where most AI assistants require sending your data to someone else's server, AI Rescue USB is built the other way: your computer's problems stay on your computer.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      🖥️  USER (Text or Voice)                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              🧠 Conversation Manager (orchestrator)             │
│   • Detects intent  • Routes to correct flow  • Remembers       │
└─────────┬──────────┬──────────┬──────────┬──────────┬──────────┘
          │          │          │          │          │
          ▼          ▼          ▼          ▼          ▼
   ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │ INSTALL  │ │ REPAIR │ │ BACKUP │ │RECOVER │ │DIAGNOSE│
   │ (OS)     │ │ (Win/  │ │ (files │ │(deleted│ │(health│
   │          │ │Lin/BSD)│ │ & disk)│ │files)  │ │check)  │
   └────┬─────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
        │           │          │          │          │
        └───────────┴──────────┴──────────┴──────────┘
                          │
                          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │              🔧 Hardware + OS Detection Layer                │
   │   • CPU, RAM, GPU, disk, network  • Windows/Linux/BSD/macOS │
   └─────────────────────────────────────────────────────────────┘
                          │
                          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │              🔒 Security Manager (triple safety)              │
   │   ① Preview  ② Backup before risky ops  ③ Explicit consent  │
   └─────────────────────────────────────────────────────────────┘
```

Everything runs **offline** on a minimal Linux live system (Alpine-based). The AI, the tools, the recovery — nothing needs the internet except downloading an OS image.

---

## 📦 Current Prototype Status

The core of AI Rescue USB is already built and testable:

| Component | Status | Notes |
|-----------|--------|-------|
| 🗣️ Conversation engine (text) | ✅ Working | Guided flows + free-form fallback, covered by tests |
| 🧠 Local LLM | 🟡 Prototype | Real inference via llama.cpp; ships with a tiny demo model, quality scales with model size — see [Quick Start](#-quick-start-for-developers) |
| 🔧 Install flow (Win/Lin/BSD) | ✅ Working | 9 OS supported, compatibility check |
| 🛠️ Repair flow (boot/grub/fs) | ✅ Working | Windows, Linux, BSD — executes for real after explicit confirmation |
| 💾 Backup flow | ✅ Working | File + disk image |
| 🔍 Recovery flow | ✅ Working | Deleted files, failing drives |
| 🩺 Diagnose flow | ✅ Working | Hardware + OS analysis |
| 🦠 Antivirus flow | 🟡 Prototype | ClamAV integration |
| 🌐 Network flow | 🟡 Prototype | WiFi, diagnostics |
| 🔌 Driver installer | 🟡 Prototype | Auto-detect + install |
| 🖼️ Web UI | ✅ Working | Modern chat interface |
| 📀 ISO builder | 🟡 Prototype | Docker + Alpine, not yet booted on real hardware |
| 🎙️ Voice (Whisper + Piper) | ⏳ Planned | Not started |

The conversation engine, repair flow, and LLM wiring are covered by [automated tests](tests/). The ISO itself hasn't been built and booted end-to-end yet — that's the next milestone.

---

## 🛣️ Roadmap

### Phase 1 — Real Bootable ISO (NOW)
- [ ] Finalize Alpine-based live system
- [ ] Embed Python + AI core
- [ ] Build and test on real hardware (UEFI + Legacy BIOS)
- [ ] Bundle ClamAV + TestDisk + PhotoRec

### Phase 2 — Offline Voice
- [ ] Integrate Whisper.cpp for offline STT
- [ ] Integrate Piper TTS for replies
- [ ] Wake word detection ("Hey Rescue")

### Phase 3 — Smarter AI
- [ ] Replace rule-based fallback with Phi-3 or Qwen
- [ ] Add memory across turns
- [ ] Multi-language support (FR/ES/DE/ZH)

### Phase 4 — Community
- [ ] Plugin system for community-built skills
- [ ] Shared repair logs (anonymous) that improve everyone's experience
- [ ] Marketplace of ISO images (offline-friendly)

---

## 🤝 How to Contribute

**We're at the beginning. Your help shapes what this project becomes.**

The single most impactful contribution right now is **feedback on the vision**:

- 🔥 Does the vision make sense? What's missing?
- 🧪 Try the prototype, break it, tell us how
- 📚 Suggest repair scenarios we haven't covered
- 🌍 Translate (French and Spanish would be huge)
- 🎨 Improve the UI — make it even simpler

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

**Rule of thumb:** If you're unsure whether your contribution fits, open an issue first. We'd rather hear 100 ideas than 0.

---

## ⚡ Quick Start (for developers)

```bash
# Clone
git clone https://github.com/leduc1984/ai-rescue-usb.git
cd ai-rescue-usb

# Install dependencies
pip install -r requirements.txt

# Optional: local LLM support — see requirements-llm.txt for a prebuilt
# wheel option (no compiler needed on Windows/Linux/macOS CPU-only).
# Skip this and the engine falls back to rule-based mode.
pip install -r requirements-llm.txt

# Optional: download a small local model to actually run it (~670MB).
# LocalLLM picks up any .gguf file placed in models/, whatever its name.
mkdir -p models
curl -L -o models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf

# Run the UI locally
python ui/server.py
# Open http://localhost:8080

# Run tests
python -m pytest tests/
```

See [INSTALL.md](INSTALL.md) for building the bootable ISO.

---

## 🛡️ Safety Philosophy

Nothing destructive happens without **three things**:

1. A clear description of what will be changed
2. An automatic backup created first
3. An explicit "yes" from the user

Every risky operation follows this pattern. No exceptions.

---

## 🎯 Real-World Scenarios

| Scenario | Before AI Rescue USB | With AI Rescue USB |
|----------|---------------------|-------------------|
| "Windows won't boot" | Pay $150, wait 3 days | Fix in 2 minutes, free |
| "Deleted my photos" | Recovery software + confusion | "What photos?" → Recovered |
| "Install Ubuntu" | Read a 2-hour tutorial | "Install Ubuntu" → Done in 15 min |
| "Grandma's PC is slow" | Drive there, fix it, drive back | Mail her a USB, call in 30 minutes |
| "PC failing, need data" | Quote $500 professional recovery | "Recover my files" → Saved in 1 hour |

---

## 📄 License

MIT — use it, fork it, ship it. See [LICENSE](LICENSE).

---

## 💬 Community

- 🐛 [Issues](https://github.com/leduc1984/ai-rescue-usb/issues) — bugs & features
- 💡 [Discussions](https://github.com/leduc1984/ai-rescue-usb/discussions) — ideas & questions
- 🐦 Follow progress: [#airesecueusb](https://twitter.com/search?q=%23airescueusb)

---

## 🙌 A Final Word

AI Rescue USB is **ambitious**. Our goal is to create an AI assistant that helps people perform computer repairs that traditionally require a technician — for the basic problems that shouldn't need one.

If this vision resonates with you, **star the repo**, share it, or — best of all — **jump in**. We need people who care about making technology accessible to everyone.

> *"The best time to plant a tree was 20 years ago. The second best time is now."*
>
> Let's plant this tree.

---

**Built with ❤️ for everyone who's ever stared at a broken screen, wondering what to do next.**

Made in Canada 🇨🇦
