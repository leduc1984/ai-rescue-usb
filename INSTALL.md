# AI Rescue USB - Installation Guide

This guide explains how to create and use your AI Rescue USB drive.

## Current Status

**There is no pre-built ISO release yet.** The project is in active development — see the
[README](README.md) for status. To try it today, you build the ISO from source. This guide
will be updated with a simple download-and-flash flow once a release exists.

## Quick Start (build from source)

### What You Need
- USB drive (8GB or larger)
- Docker (recommended) or the tools listed in [CONTRIBUTING.md](CONTRIBUTING.md)
- Target computer (to rescue)

### Step 1: Build the ISO

```bash
git clone https://github.com/leduc1984/ai-rescue-usb.git
cd ai-rescue-usb
./build-all.sh
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the build details and what to do if it fails —
this hasn't been verified end-to-end on real hardware yet, so expect rough edges.

### Step 2: Flash to USB

**On Linux/macOS:**
```bash
sudo ./flash-usb-linux.sh
```

**On Windows:**
```powershell
flash-usb-windows.bat
```

Both scripts are in the repo root and write the ISO built in Step 1 to a USB drive you select.
Alternatively, use [Rufus](https://rufus.ie) (Windows) or [BalenaEtcher](https://www.balena.io/etcher/)
(any OS) and point it at the ISO in `build/`.

### Step 3: Boot from USB

1. Insert USB into the target computer
2. Restart the computer
3. Enter boot menu (usually F12, F2, ESC, or DEL during startup)
4. Select "USB" or "Removable Device"
5. Wait for AI Rescue USB to load (30-60 seconds)

**Boot menu keys by manufacturer:**
- Dell: F12
- HP: F9 or F10
- Lenovo: F12 or Nova button
- Asus: F8 or Esc
- Acer: F12
- Toshiba: F12
- Apple: Option (Alt) key
- Samsung: F10 or Esc

### Step 4: Use the AI

The AI will greet you automatically. Just explain what you need:

**Examples:**
- "My Windows won't boot" → AI diagnoses and fixes
- "Install Ubuntu" → AI guides through installation
- "Recover my deleted photos" → AI recovers files
- "My computer is slow" → AI runs diagnostics

That's it! The AI handles everything else.

---

## Detailed Instructions

### Verifying the Build

After `./build-all.sh` completes, it prints a SHA256 checksum for the ISO it produced.
Save that checksum if you plan to flash the same ISO onto multiple drives, so you can confirm
later that a copy wasn't corrupted:

```bash
# Linux/macOS
sha256sum build/ai-rescue-usb.iso

# Windows (PowerShell)
Get-FileHash build\ai-rescue-usb.iso -Algorithm SHA256
```

### Creating USB on Different Operating Systems

#### Windows

**Option 1: repo script**
```powershell
flash-usb-windows.bat
```

**Option 2: Rufus**
```
1. Download Rufus: https://rufus.ie
2. Insert USB drive
3. Open Rufus
4. Under "Device", select your USB drive
5. Under "Boot selection", click "SELECT" and choose build\ai-rescue-usb.iso
6. Leave other settings as default
7. Click "START"
8. If prompted, choose "Write in ISO Image mode"
9. Wait for completion (5-10 minutes)
```

#### Linux

**Option 1: repo script**
```bash
sudo ./flash-usb-linux.sh
```

**Option 2: dd (manual)**
```bash
# 1. Find your USB drive
lsblk
# Look for your USB (e.g., /dev/sdb) — make sure you select the RIGHT drive!

# 2. Unmount the USB (if mounted)
sudo umount /dev/sdX*

# 3. Flash the ISO
sudo dd if=build/ai-rescue-usb.iso of=/dev/sdX bs=4M status=progress conv=fsync
sudo sync
```

#### macOS

No dedicated script yet — use dd or a GUI tool:

```bash
# 1. Find your USB drive
diskutil list
# Look for your USB (e.g., /dev/disk2) — make sure you select the RIGHT drive!

# 2. Unmount the USB
diskutil unmountDisk /dev/diskN

# 3. Flash the ISO (use rdiskN for faster writes)
sudo dd if=build/ai-rescue-usb.iso of=/dev/rdiskN bs=4m

# 4. Eject
diskutil eject /dev/diskN
```

Or use [BalenaEtcher](https://www.balena.io/etcher/): Flash from file → select the ISO →
select your USB drive → Flash.

### Booting from USB

#### BIOS/UEFI Settings

**Step 1: Enter BIOS/UEFI**
```
1. Restart computer
2. Immediately press BIOS key repeatedly:
   - Dell: F2
   - HP: F10 or Esc then F10
   - Lenovo: F2 or Fn+F2
   - Asus: F2 or Del
   - Acer: F2 or Del
   - Toshiba: F2
   - Samsung: F2
3. BIOS screen should appear
```

**Step 2: Disable Secure Boot (if needed)**
```
1. Navigate to "Security" or "Boot" tab
2. Find "Secure Boot" option
3. Set to "Disabled"
4. Save and exit (usually F10)
```

**Step 3: Change Boot Order**
```
1. Navigate to "Boot" tab
2. Find "Boot Order" or "Boot Priority"
3. Move "USB" or "Removable Device" to top
4. Save and exit
```

**Step 4: Boot**
```
1. Insert AI Rescue USB
2. Restart computer
3. It should boot from USB automatically
4. If not, press boot menu key during startup:
   - Dell: F12
   - HP: F9
   - Lenovo: F12 or Nova button
   - Asus: F8
   - Acer: F12
   - Toshiba: F12
5. Select USB from boot menu
```

### First Boot

When AI Rescue USB boots:

1. **Loading Screen** (10-30 seconds)
   - You'll see AI Rescue USB logo
   - System is loading

2. **Hardware Detection** (10-20 seconds)
   - AI scans your hardware
   - Detects drives, OS, etc.

3. **Welcome Screen**
   - AI greets you
   - "Hello! How can I help you today?"

4. **Ready to Use**
   - Type or speak your request
   - AI will guide you

### Using the AI

**Text Interface:**
```
Just type your request in the chat box:
- "My computer won't boot"
- "Install Windows 11"
- "Recover my files"
- "Diagnose my computer"
```

**Voice Interface (if available):**
```
1. Click microphone icon
2. Speak your request
3. AI listens and responds
4. Continue conversation
```

**Common Requests:**

| You Say | AI Does |
|---------|---------|
| "Windows won't boot" | Diagnoses and repairs boot issues |
| "Install Ubuntu" | Guides through Linux installation |
| "Recover deleted photos" | Scans and recovers files |
| "Computer is slow" | Runs diagnostics, suggests fixes |
| "Backup my files" | Creates backup to external drive |
| "Install Windows 11" | Downloads and installs Windows |

### After Use

**Shutdown:**
```
1. Click "Shutdown" in the menu
2. Wait for system to power off
3. Remove USB drive
```

**Restart Target Computer:**
```
1. Remove USB drive
2. Restart computer
3. It should boot normally from its internal drive
```

---

## Troubleshooting

### USB Won't Boot

**Problem:** Computer doesn't boot from USB

**Solutions:**
1. **Check BIOS boot order**
   - Enter BIOS (see above)
   - Make sure USB is first in boot order
   - Save and exit

2. **Disable Secure Boot**
   - Some systems require this
   - See "BIOS/UEFI Settings" above

3. **Try different USB port**
   - Use USB 2.0 port if available
   - Avoid USB hubs

4. **Re-flash USB**
   - Rebuild the ISO (`./build-all.sh`) in case the build was incomplete
   - Flash with a different method (Rufus, Etcher, etc.)

5. **Try different USB drive**
   - Some drives don't work well
   - Use name brand (SanDisk, Kingston, etc.)

### Flash Failed

**Problem:** USB flashing fails

**Solutions:**
1. **Check USB drive**
   - Must be 8GB or larger
   - Try different drive if fails

2. **Run as administrator/root**
   - Windows: Right-click → Run as Admin
   - Linux/macOS: Use sudo

3. **Close other programs**
   - Antivirus may block
   - Close disk utilities

4. **Format USB first**
   - Format as FAT32
   - Try flashing again

### AI Won't Start

**Problem:** USB boots but AI doesn't load

**Solutions:**
1. **Check hardware requirements**
   - Need 2GB+ RAM
   - Need x86_64 processor
   - Need USB 2.0+

2. **Try compatibility mode**
   - Add boot parameter: `nomodeset`
   - Or: `acpi=off`

3. **Check logs**
   - Press Ctrl+Alt+F2 for console
   - Check /var/log/ai-rescue.log

4. **Re-flash USB**
   - ISO might be corrupted
   - Flash again with verified ISO

### AI Doesn't Understand

**Problem:** AI doesn't respond correctly

**Solutions:**
1. **Be specific**
   - ❌ "Fix computer"
   - ✅ "My Windows won't boot, shows blue screen"

2. **Use simple language**
   - Avoid technical jargon
   - Describe symptoms

3. **Try text instead of voice**
   - Voice recognition might fail
   - Type request instead

4. **Restart AI**
   - Close and reopen chat
   - Or reboot USB

### Can't Find My Files

**Problem:** AI can't locate files to recover

**Solutions:**
1. **Check drive is connected**
   - External drives must be plugged in
   - AI should detect automatically

2. **Mount drive manually**
   - Click "File Manager"
   - Navigate to drive
   - Click to mount

3. **Specify path**
   - Tell AI where to look
   - "Check /dev/sdb1 for photos"

---

## FAQ

**Q: Will this erase my data?**  
A: No. AI Rescue USB automatically backs up before doing anything risky. It always asks for confirmation.

**Q: Do I need internet?**  
A: No. Core features work offline. Internet only needed for downloading OS images or driver updates.

**Q: Can it fix a completely dead computer?**  
A: If the computer can power on and display video, yes. If hardware is physically broken, we can only rescue data.

**Q: How long does it take?**  
A: Boot: 30-60 seconds. Diagnosis: 1-2 minutes. Repair: 2-10 minutes. OS install: 15-30 minutes.

**Q: What if something goes wrong?**  
A: Every risky operation creates a backup first. If anything fails, you can restore the backup.

**Q: Is it free?**  
A: Yes, 100% free and open source. No hidden costs, no subscriptions.

**Q: Which computers does it work on?**  
A: Any x86_64 computer (Intel/AMD) from 2005 or newer. Works with BIOS or UEFI.

**Q: Can I use it on a Mac?**  
A: Intel Macs: planned. Apple Silicon (M1/M2/M3): not planned yet — see the [README roadmap](README.md).

> The timings and behavior above describe the intended design. Since the ISO hasn't been
> tested end-to-end on real hardware yet, treat them as goals rather than measured results
> until this note is removed.

---

## Getting Help

If you're stuck:

1. **Read this guide** - Most questions answered here
2. **Check FAQ** - Common issues and solutions
3. **[GitHub Issues](https://github.com/leduc1984/ai-rescue-usb/issues)** - Report bugs or ask questions
4. **[GitHub Discussions](https://github.com/leduc1984/ai-rescue-usb/discussions)** - Ideas and questions

---

**Good luck! 🚀**
