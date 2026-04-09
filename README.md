<div align="center">

# 👋 SpankUrLaptop

**Your laptop has senses now. Slap it. It screams back.**  
Harder slap = louder reaction. Calibrated to *you*. Works on every laptop ever made.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>
<img width="1024" height="1536" alt="file_0000000077dc71f58dae53c06f8b3449" src="https://github.com/user-attachments/assets/2dfa6e95-be3a-4deb-857c-cd21f0c81e99" />
---

## 🤔 Why This Exists

SlapMac went viral. The concept was brilliant.

But every Mac slap tool — SlapMac, spank, SmackMac, SlapMyMac — is **locked to Apple Silicon.**  
They all depend on the built-in accelerometer that only exists in M-series MacBooks.

**No accelerometer? No tool.**

Windows users, Linux users, older Mac users — completely locked out.

So I re-engineered the entire detection layer from scratch using a completely different approach:  
**microphone-based real-time signal processing.**

No accelerometer required. Works on any laptop ever made.

---

## 🔬 The Re-Engineering: How Detection Actually Works

Mac tools take the easy path — read a G-force spike from hardware, play a sound.  
That's a clean 1-sensor problem.

Microphone detection is a fundamentally harder problem.  
A mic hears **everything** — your voice, keyboard, music, phone buzzing, AC units, anything.  
The tool has to figure out, in real time, with zero latency, which audio event was specifically a **chassis slap.**

Here's the 4-layer filter stack built to solve this:

### Layer 1 — Volume Spike Gate
```
RMS > 5× rolling baseline
```
First pass. Filters out all ambient noise. Only events that are dramatically louder than the last 2 seconds of audio pass through. Typing, voice, background music — all rejected here.

### Layer 2 — Crest Factor Analysis
```
Peak / RMS > 3.0
```
A physical impact (slap) is an **impulse** — an extremely sharp, instantaneous spike followed by silence. Voice and music are sustained signals with low crest factors. This filter mathematically distinguishes a chassis thud from anything sustained, including loud voices or bass-heavy music.

### Layer 3 — FFT Frequency Fingerprinting + Cosine Similarity
```
Cosine Similarity ≥ 82% against your calibrated profile
```
This is the core re-engineering. Every laptop chassis has a **unique resonance frequency** when struck — determined by its material, thickness, size, and internal structure. During calibration, the tool computes an FFT (Fast Fourier Transform) of each of your slaps and builds an averaged frequency fingerprint unique to your machine and your hitting style. At runtime, every spike that passes Layers 1 and 2 gets its FFT computed and compared against your profile using cosine similarity. Only a match ≥ 82% triggers a reaction.

### Layer 4 — Volume Gate Against Calibrated Baseline
```
RMS ≥ 40% of your calibrated average spank volume
```
Final pass. Filters out keyboard clicks and light taps that somehow passed the earlier layers. The reaction only fires if the hit is meaningfully loud relative to how hard you actually slap.

**All 4 layers in 5.8ms.** BLOCK_SIZE = 256 samples at 44,100Hz.

---

## 🎛️ Personal Calibration System

```bash
spankurlaptop calibrate            # 100 spanks — maximum precision
spankurlaptop calibrate --count 20 # 20 spanks — quick start
```

The calibration system records N slaps from your specific laptop chassis and your specific hitting style, computes the average FFT spectrum across all samples, normalizes it into a unit vector, and saves it as a `.npz` profile in your home directory.

The result: the tool is tuned to **your hands on your machine.** Nobody else's slap pattern will trigger it.

> 💡 More samples = tighter profile = fewer false positives. 100 is the gold standard. 20 gets you 80% of the way there.

---

## 🆚 SpankUrLaptop vs Mac Slap Tools

| | SpankUrLaptop | SlapMac / spank / SmackMac |
|---|---|---|
| **Windows** | ✅ | ❌ |
| **Linux** | ✅ | ❌ |
| **Older Macs** | ✅ | ❌ |
| **Detection Method** | FFT + Cosine Similarity | Accelerometer (hardware) |
| **Personalized to your chassis** | ✅ Calibrated profile | ❌ Generic threshold |
| **False positive filtering** | 4-layer signal stack | Basic G-force threshold |
| **Calibration control** | `--count` flag, any N | Fixed sensitivity slider |
| **Open Source** | ✅ MIT | Some paid, some open |
| **Control Panel** | ✅ Ctrl+5 UI | Varies |
| **PyPI installable** | ✅ | ❌ |

---

## 📦 Installation Guide

### Method A — Install directly from GitHub (Fastest)

```bash
pip install git+https://github.com/NithinVarma50/spankurlaptop.git
```

One command. `audio.zip` (59 reaction sounds) bundles automatically — no manual file copying, no GitHub account needed.

### Method B — Install locally from source

```bash
git clone https://github.com/NithinVarma50/spankurlaptop.git
cd spankurlaptop
pip install .
```

> ⚠️ **Python 3.8+ required.** On Windows, check **"Add Python to PATH"** during Python installation.

---

### Step 2 — Audio Files (Bundled Automatically ✅)

`audio.zip` is **bundled inside the package** and loads automatically after install — no manual file copying needed.

---

### Step 3 — Calibrate Your Laptop (Do This Once!)

This step teaches the tool the **unique thud sound of your specific laptop chassis** so it ignores all other sounds (typing, voice, music).

```bash
# Default: calibrate with 100 spanks (recommended)
spankurlaptop calibrate

# Quick calibration: choose any number
spankurlaptop calibrate --count 20
spankurlaptop calibrate --count 30
```

Spank your laptop the chosen number of times, pausing about a second between each slap. The tool records the frequency fingerprint and volume of each slap to build a precision profile unique to your machine.

When done, it saves a `.spankurlaptop_profile.npz` in your user home directory.

> 💡 Slap the area around the **trackpad or palm rest** for the most consistent results.

---

## 🚀 Usage

Since it's installed globally, run these commands from **anywhere** in your terminal.

### ▶️ Start (runs silently in the background)

```bash
spankurlaptop start
```

Launches in the background with no terminal window. Close the terminal — it keeps running.

---

### ⏹️ Stop

```bash
spankurlaptop stop
```

Sends a termination signal and removes the PID file cleanly.

> ⚠️ If `stop` says "Not running" but you think it's still active, run `status` to check.

---

### 📊 Check Status

```bash
spankurlaptop status
```

```
spankurlaptop is RUNNING (PID: 18472)
```
or
```
spankurlaptop is NOT running.
```

---

### 🔁 Re-Calibrate Anytime

If you move to a different laptop or detection feels off:

```bash
spankurlaptop calibrate
spankurlaptop calibrate --count 20
```

---

### 🔊 Test Audio

Play a random sound instantly to verify everything is working:

```bash
spankurlaptop test-audio
```

---

### 🧪 Run in Foreground (for debugging)

```bash
spankurlaptop run
```

Visible output in terminal. Ctrl+C to quit.

---

### 🗑️ Uninstall

```bash
spankurlaptop uninstall
pip uninstall spankurlaptop
```

Stops any running process and removes all config files cleanly.

---

## 🎛️ Control Panel

Press **`Ctrl + 5`** anytime after starting to open the hidden settings UI.

- Toggle the tool **On / Off**
- Adjust **Master Volume**
- Adjust **Slap Sensitivity**
- **Test Scream** button
- See whether it's using **Accelerometer** or **Microphone** mode

Close the window — tool keeps running invisibly in the background.

---

## 🎵 Audio Reactions

59 reactions pre-loaded into RAM at startup for zero-latency playback, mapped across 5 intensity buckets:

| Bucket | Slap Intensity | Sound Range |
|--------|---------------|-------------|
| 1 | Very light (< 20%) | Sounds 01–11 |
| 2 | Light (20–40%) | Sounds 12–23 |
| 3 | Medium (40–60%) | Sounds 24–35 |
| 4 | Hard (60–80%) | Sounds 36–47 |
| 5 | Very hard (80–100%) | Sounds 48–59 |

---

## 📁 Project Structure

```
spankurlaptop/
├── spankurlaptop/          # Package source
│   ├── __init__.py         # Main logic & listener
│   ├── __main__.py         # Entry point for background process
│   └── audio.zip           # 59 audio reaction files
├── setup.py                # Installation script
├── MANIFEST.in             # Ensures audio.zip is bundled
├── requirements.txt        # Python dependencies
└── README.md
```

---

## 🛠 Requirements

- Python 3.8+
- A working microphone (built-in laptop mic works perfectly)
- A laptop you're willing to slap

---

## ❓ Troubleshooting

**`Dependencies missing!` error on launch**  
→ Run `pip install -r requirements.txt` and make sure your venv is activated.

**`audio.zip not found` warning**  
→ Reinstall:
```bash
pip install --force-reinstall git+https://github.com/NithinVarma50/spankurlaptop.git
```

**Tool doesn't react to slaps**  
→ Run `calibrate` again and slap more firmly during calibration.

**`stop` says "Not running" but it is**
```bash
# Windows
taskkill /F /IM python.exe

# macOS / Linux
pkill -f "python -m spankurlaptop"
```

**`sounddevice` install fails on Linux**
```bash
sudo apt install libportaudio2 portaudio19-dev
pip install sounddevice
```

---

## 📜 License

MIT — slap freely.

