<div align="center">

# 👋 SpankUrLaptop

**A terminal background tool that gives your laptop senses.**  
Slap it. It screams back. Harder slap = louder scream.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

---

## 🧠 How It Works

SpankUrLaptop runs silently in the background and listens through your laptop's microphone.

When you slap your laptop, it:

1. **Detects the impact instantly** — using a real-time audio spike detector with an `11ms` audio block size, faster than human reaction time.
2. **Analyzes the wave** — computes an FFT (Fast Fourier Transform) frequency fingerprint and matches it against your calibrated slap profile.
3. **Filters out false positives** — voice, typing, and phone notifications are rejected using a Crest Factor + Cosine Similarity test.
4. **Screams back in proportion** — maps the slap intensity (0–100%) to one of 59 progressively louder audio reactions, chosen randomly from the correct intensity bucket.

---

## 📦 Installation

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/spankurlaptop.git
cd spankurlaptop
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Requirements**: `numpy`, `sounddevice`, `pygame`, `psutil`

### 3. Calibrate your laptop (do this once!)

This step teaches the tool your laptop's specific slap sound wave — so it ignores all other sounds.

```bash
python spankurlaptop.py calibrate
```

You will be asked to **spank your laptop 100 times** 🔥, pausing slightly between each. The tool will record the frequency fingerprint and volume of each slap to build a precision profile.

---

## 🚀 Usage

### Start (runs in the background, no terminal window)

```bash
python spankurlaptop.py start
```

### Stop

```bash
python spankurlaptop.py stop
```

### Check if it's running

```bash
python spankurlaptop.py status
```

### Re-calibrate anytime

```bash
python spankurlaptop.py calibrate
```

---

## 🎵 Audio Variants

The tool ships with **59 audio reactions** stored in `audio.zip`, all pre-loaded into RAM at startup for zero-latency playback. Reactions are mapped across 5 intensity buckets:

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
| Frequency Match | Cosine Similarity ≥ 92% | Matches your unique chassis thud pattern |
| Volume Gate | RMS ≥ 60% of calibrated average | Filters keyboard clicks |

---

## 📁 Project Structure

```
spankurlaptop/
├── spankurlaptop.py       # Main CLI tool
├── requirements.txt        # Python dependencies
├── audio.zip               # 59 audio reaction files (01.mp3 – 59.mp3)
├── spank_profile.npz       # Your saved calibration profile (auto-generated)
└── .gitignore
```

---

## 🛠 Requirements

- Python 3.8+
- A working microphone
- A laptop you're willing to slap

---

## 📜 License

MIT — slap freely.
