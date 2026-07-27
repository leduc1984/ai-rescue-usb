# Future Ideas

This is a backlog of ideas, **not a committed roadmap**. None of this is scheduled or
promised — see the Roadmap section of the [README](README.md) for what's actually being
worked on next. Items here are things that could make sense later, roughly grouped by theme.

## Voice & AI
- Offline speech-to-text (Whisper.cpp) and text-to-speech (Piper)
- A stronger local LLM (e.g. Phi-3-mini) once the rule-based fallback is solid
- Multi-language support beyond French/English

## Hardware & compatibility
- ARM64 support (Apple Silicon)
- Better support for pre-2010 hardware (low RAM, IDE/PATA)
- USB-C / Thunderbolt boot

## Recovery
- BitLocker / FileVault-aware recovery flow
- Windows local password reset (chntpw)
- Malware scanning (ClamAV) before repairs

## Installation
- Unattended OS installs (autounattend.xml, preseed, kickstart)
- Automatic driver matching and installation

## Safety
- A read-only "safe mode" for diagnosis without any risk of modification
- Encrypted audit logs

## Diagnostics
- Hardware benchmarks (CPU/RAM/disk/GPU)
- Predictive disk failure from SMART data

## Contributing an idea
If one of these (or something not listed) sounds interesting to build, open an issue first —
see [CONTRIBUTING.md](CONTRIBUTING.md).
