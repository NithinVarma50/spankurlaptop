<div align="center">

# 👋 SpankUrLaptop

**A terminal background tool that gives your laptop senses.**  
Slap it. It screams back. Harder slap = louder scream.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

---

## 🧠 How It Works

SpankUrLaptop runs silently in the background and listens through your laptop's **built-in accelerometer** or **microphone**.

When you slap your laptop chassis, it:

1. **Detects the impact instantly** — automatically uses your accelerometer (if available) for precision spike detection, or falls back to a real-time audio spike detector via microphone.
2. **Analyzes the wave** — computes the mechanical force (via accelerometer) or frequency fingerprint (via microphone) to confirm a spank.
3. **Filters out false positives** — completely ignores voice, keyboard typing, and ambient noise.
4. **Screams back in proportion** — maps the slap intensity (0–100%) to one of 59 progressively louder audio reactions, chosen randomly from the correct intensity bucket.

---

## 🎛️ Control Panel

SpankUrLaptop now comes with a hidden Control Panel!

Once the tool is started, you can press **`Ctrl + 5`** globally on your keyboard to reveal the UI.
From the Control Panel you can:
- Toggle the tool **On/Off**.
- Adjust **Master Volume**.
- Adjust **Slap Sensitivity**.
- Use the **Test Scream** button.
- See whether it's using the **Accelerometer** or **Microphone**.
When you are done, simply hit the **X** button to close the UI, and the tool will become invisible again while continuing to run in the background.

---

## 📦 Installation Guide

Follow these steps **exactly** to install `spankurlaptop` globally over your terminal.

---

### Method A — Install directly from GitHub (Fastest)

Just like `npm install -g`, you can install this globally using Python's package manager:

```bash
pip install git+https://github.com/NithinVarma50/spankurlaptop.git
```

### Method B — Install locally from source

Alternatively, clone the repository and install it directly:

```bash
git clone https://github.com/NithinVarma50/spankurlaptop.git
cd spankurlaptop
pip install .
```

> ⚠️ **Make sure you have Python 3.8+ installed** and `pip` available in your terminal. For Windows, check **"Add Python to PATH"** during installation.

---

### Step 2 — Audio Files (Bundled Automatically ✅)

`audio.zip` is **bundled inside the package** and loads automatically after install — no manual file copying needed.

---

### Step 3 — Calibrate Your Laptop (Do This Once!)

This step teaches the tool the **unique thud sound of your specific laptop chassis** so it ignores all other sounds (typing, voice, music).

```bash
# Default: calibrate with 100 spanks
spankurlaptop calibrate

# Quick calibration: choose any number (e.g. 20 or 30)
spankurlaptop calibrate --count 20
spankurlaptop calibrate --count 30
```

Spank your laptop the chosen number of times, pausing about a second between each slap. The tool records the frequency fingerprint and volume of each slap to build a precision profile.

When done, it saves a `.spankurlaptop_profile.npz` in your user home directory.

> 💡 Slap the area around the **trackpad or palm rest** for the most consistent results.
> 
> 💡 More spanks = more accurate profile. 20–30 is fine for a quick start; 100 gives best precision.

---

## 🚀 Usage

Since it's installed globally, you can type these commands from **anywhere** in your terminal!

### ▶️ Start (runs silently in the background)

```bash
spankurlaptop start
```

The tool will launch in the background with **no terminal window**. You can now close the terminal — it keeps running.

---

### ⏹️ Stop

To stop the background process:

```bash
spankurlaptop stop
```

This sends a termination signal to the background process and removes the PID file cleanly.

> ⚠️ If `stop` says "Not running" but you think it's still active, run `status` to check, or restart your terminal session.

---

### 📊 Check Status

```bash
spankurlaptop status
```

Output example:
```
spankurlaptop is RUNNING (PID: 18472)
```
or
```
spankurlaptop is NOT running.
```

---

### 🔁 Re-Calibrate Anytime

If you move to a different laptop or the detection feels off:

```bash
# Full calibration (100 spanks)
spankurlaptop calibrate

# Quick re-calibration (20 spanks)
spankurlaptop calibrate --count 20
```

---

### 🧪 Run in Foreground (for debugging)

To run the detector directly in your terminal (visible output, Ctrl+C to quit):

```bash
spankurlaptop run
```

---

### 🗑️ Uninstall

To completely remove spankurlaptop from your system:

```bash
spankurlaptop uninstall
pip uninstall spankurlaptop
```

This stops any running process, removes configuration files, and provides instructions for full uninstallation.

---

## 🎵 Audio Reactions

59 reactions in `audio.zip`, pre-loaded into RAM at startup for zero-latency playback, mapped across 5 intensity buckets:

| Bucket | Slap Intensity | Sound Range |
|--------|---------------|-------------|
| 1 | Very light (< 20%) | Sounds 01–11 |
| 2 | Light (20–40%) | Sounds 12–23 |
| 3 | Medium (40–60%) | Sounds 24–35 |
| 4 | Hard (60–80%) | Sounds 36–47 |
| 5 | Very hard (80–100%) | Sounds 48–59 |

---

## 🔬 Detection Tech

| Layer | Filter | Purpose |
|-------|--------|---------|
| Volume Spike | RMS > 5× baseline | Ignores ambient noise |
| Crest Factor | Peak/RMS > 3.0 | Filters sustained sounds (voice, music) |
| Frequency Match | Cosine Similarity ≥ 82% | Matches your unique chassis thud pattern |
| Volume Gate | RMS ≥ 40% of calibrated average | Filters keyboard clicks |

---

## 📁 Project Structure

```
spankurlaptop/
├── spankurlaptop/          # Package source
│   ├── __init__.py         # Main logic & listener
│   ├── __main__.py         # Entry point for background process
│   └── audio.zip           # 60+ audio reaction files
├── setup.py                # Installation script
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
→ Run `pip install -r requirements.txt` again, and make sure your venv is activated.

**`audio.zip not found` warning**
→ The audio files are bundled inside the package. Try reinstalling:
```bash
pip install --force-reinstall git+https://github.com/NithinVarma50/spankurlaptop.git
```

**Tool doesn't react to slaps**
→ Run `calibrate` again and slap more firmly during calibration.

**`stop` says "Not running" but it is**
→ Manually find and kill the process:
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
