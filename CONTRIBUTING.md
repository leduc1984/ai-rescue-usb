# AI Rescue USB - Development Guide

This guide explains how to develop, test, and build AI Rescue USB from source.

## Prerequisites

### Required
- **Python 3.11+** with pip
- **Node.js 18+** with npm
- **Git**

### For Building ISO
- **Docker** (recommended) OR
- **QEMU**, **mtools**, **xorriso**, **syslinux**

### For Testing
- **QEMU** for virtual testing
- Real USB drive (8GB+) for hardware testing

## Development Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/ai-rescue-usb.git
cd ai-rescue-usb
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Node Dependencies (for UI)
```bash
cd ui
npm install
cd ..
```

### 4. Run Development Server
```bash
# This starts the web UI on http://localhost:8080
python ui/server.py
```

### 5. Test the Conversation System
```bash
# Run verification tests
python C:/Users/Leduc/AppData/Local/Temp/hermes-verify-conversation.py

# You should see: ✅ ALL 10/10 CHECKS PASSED
```

## Architecture Overview

```
ai-rescue-usb/
├── ai_core/                    # Core AI system
│   ├── engine.py              # Main AI engine
│   ├── voice_system.py        # Voice recognition/TTS
│   └── conversation/          # Conversation flows
│       ├── conversation_manager.py
│       ├── universal_assistant.py
│       ├── install_flow.py
│       ├── repair_flow.py
│       ├── backup_flow.py
│       ├── recovery_flow.py
│       └── diagnose_flow.py
├── agents/                     # Specialized agents
│   ├── repair_agent.py
│   └── driver_agent.py
├── detection/                  # Hardware/OS detection
│   ├── hardware/
│   └── os/
├── security/                   # Safety systems
├── ui/                         # Web interface
│   ├── server.py
│   └── static/
├── scripts/                    # Build scripts
├── website/                    # Public website
└── docker/                     # Docker build environment
```

## Testing

### Unit Tests
```bash
# Test conversation system
python -m pytest tests/

# Or run specific verification
python C:/Users/Leduc/AppData/Local/Temp/hermes-verify-*.py
```

### Integration Test with QEMU
```bash
# Build ISO first
./build-all.sh

# Test in QEMU (virtual machine)
./test-in-qemu.sh
```

This will:
1. Boot AI Rescue USB in a virtual machine
2. Let you test the conversation interface
3. Test hardware detection (virtual hardware)
4. Test repair/install flows (simulated)

### Hardware Test
```bash
# Build ISO
./build-all.sh

# Flash to USB
sudo ./flash-usb-linux.sh

# Boot from USB on target hardware
# (Change BIOS/UEFI settings to boot from USB)
```

## Adding New Features

### 1. Add a New Conversation Flow

Create `ai_core/conversation/new_flow.py`:

```python
"""
AI Rescue USB - New Feature Flow
================================
"""
import logging

log = logging.getLogger("new-flow")

class NewFlow:
    def __init__(self, manager):
        self.manager = manager
        self.step = 0
        self.finished = False

    async def start(self, user_input: str) -> str:
        """Start the flow."""
        return "Welcome! What do you need help with?"

    async def handle_input(self, user_input: str) -> str:
        """Handle user input."""
        self.step += 1
        
        if self.step >= 3:
            self.finished = True
            return "✅ Task completed!"
        
        return f"Step {self.step}: Processing..."

    def is_finished(self) -> bool:
        return self.finished
```

Register in `conversation_manager.py`:

```python
from ai_core.conversation.new_flow import NewFlow

# In ConversationManager.__init__
self.flows = {
    # ... existing flows
    "new_feature": NewFlow,
}
```

Update `_detect_intent()`:

```python
def _detect_intent(self, user_input: str):
    # ... existing detections
    elif any(w in inp for w in ["new feature", "something new"]):
        return IntentType.NEW_FEATURE
```

Add to `flow_map`:

```python
flow_map = {
    # ... existing mappings
    IntentType.NEW_FEATURE: "new_feature",
}
```

### 2. Add Universal Assistant Knowledge

Edit `ai_core/conversation/universal_assistant.py`:

```python
KNOWLEDGE = {
    # ... existing knowledge
    "my_new_topic": {
        "trigger": ["my keywords"],
        "answer": "My helpful response..."
    }
}
```

### 3. Add New Agent

Create `agents/new_agent.py`:

```python
"""
New Agent
=========
"""
import logging

log = logging.getLogger("new-agent")

class NewAgent:
    def __init__(self):
        pass
    
    def do_something(self, param: str) -> dict:
        # ... implementation
        return {"success": True, "message": "Done!"}
```

## Building for Production

### Build ISO (with Docker)
```bash
./build-all.sh
```

This will:
1. Build Docker image
2. Compile Python code
3. Create ISO filesystem
4. Generate boot files
5. Create final ISO
6. Generate checksums

### Build ISO (without Docker)
```bash
./scripts/build-base.sh
cd build
./create-iso.sh
```

### Verify ISO
```bash
# Check file exists
ls -lh build/ai-rescue-usb.iso

# Verify checksum
sha256sum build/ai-rescue-usb.iso
```

### Test ISO
```bash
./test-in-qemu.sh
```

## Code Style

### Python
- Use type hints
- Follow PEP 8
- Use logging module
- Docstrings for all functions/classes

### JavaScript
- Use modern ES6+ syntax
- Comment complex logic
- Keep functions small and focused

### Shell Scripts
- Use `set -e` for error handling
- Quote variables: `"$VAR"`
- Check dependencies at startup
- Provide helpful error messages

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and test
4. Commit: `git commit -am 'Add my feature'`
5. Push: `git push origin feature/my-feature`
6. Create Pull Request

### Before Submitting PR
- [ ] All tests pass
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] No security issues introduced
- [ ] Works offline (if applicable)

## Troubleshooting

### QEMU won't start
```bash
# Check KVM support
ls -la /dev/kvm

# If not available, run without KVM (slower)
qemu-system-x86_64 -cdrom build/ai-rescue-usb.iso
```

### ISO won't build
```bash
# Check Docker is running
docker ps

# Check dependencies
which qemu-img mtools xorriso

# Try clean build
rm -rf build/
./build-all.sh
```

### Tests fail
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Run tests with verbose output
python -m pytest tests/ -v
```

## Performance Optimization

### Reduce ISO Size
- Remove unnecessary packages
- Use compression: `UPX` for binaries
- Strip debug symbols

### Faster Boot
- Minimize init scripts
- Use systemd tmpfiles
- Parallel service startup

### Better AI Performance
- Use quantized models (Q4, Q5)
- Enable GPU acceleration if available
- Cache frequent responses

## Security Checklist

- [ ] Input validation on all user inputs
- [ ] No hardcoded credentials
- [ ] Secure defaults (read-only mode available)
- [ ] Backup before destructive operations
- [ ] User confirmation for risky actions
- [ ] No data sent to external servers (offline-first)

## Resources

- [Alpine Linux Docs](https://wiki.alpinelinux.org/)
- [QEMU Documentation](https://www.qemu.org/docs/master/)
- [Python Logging](https://docs.python.org/3/library/logging.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Happy coding! 🚀**

For questions, open an issue on GitHub or join our Discord community.
