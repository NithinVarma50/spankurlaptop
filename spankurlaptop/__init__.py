import os
import sys
import argparse
import subprocess
import json
import zipfile
import io
import random
import time
import psutil

try:
    import numpy as np
    import sounddevice as sd
    from pygame import mixer
except ImportError:
    print("Dependencies missing! Please run: pip install -r requirements.txt")
    sys.exit(1)

# --- Locate audio.zip reliably regardless of install method ---
def _get_audio_zip_path():
    """Returns the path to audio.zip using importlib.resources (works after pip install)."""
    try:
        # Python 3.9+
        from importlib.resources import files
        ref = files("spankurlaptop").joinpath("audio.zip")
        # If it's a real path (not a zipimport), return it directly
        path = str(ref)
        if os.path.exists(path):
            return path
        # Otherwise, extract to a temp file
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp.write(ref.read_bytes())
        tmp.close()
        return tmp.name
    except Exception:
        pass

    try:
        import pkg_resources
        return pkg_resources.resource_filename("spankurlaptop", "audio.zip")
    except Exception:
        pass

    # Final fallback: same directory as this file
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio.zip")


PID_FILE = os.path.join(os.path.expanduser("~"), ".spankurlaptop.pid")
PROFILE_FILE = os.path.join(os.path.expanduser("~"), ".spankurlaptop_profile.npz")
SAMPLE_RATE = 44100
BLOCK_SIZE = 512  # Very small block size for near zero latency


def daemonize():
    """Starts the script as a background process depending on OS."""
    if os.path.exists(PID_FILE):
        print("Tool is already running. Try 'stop' first.")
        return

    print("Starting spankurlaptop in background...")
    if sys.platform == "win32":
        # Launch independently without a window using -m so it works after pip install
        CREATE_NO_WINDOW = 0x08000000
        startup_log = os.path.join(os.path.expanduser("~"), "spankurlaptop_startup_error.log")
        with open(startup_log, "w") as err_file:
            p = subprocess.Popen(
                [sys.executable, "-m", "spankurlaptop", "run"],
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=err_file
            )
        with open(PID_FILE, "w") as f:
            f.write(str(p.pid))
        print(f"Started! PID: {p.pid}")
    else:
        # Fork on Unix/macOS
        pid = os.fork()
        if pid > 0:
            with open(PID_FILE, "w") as f:
                f.write(str(pid))
            print(f"Started! PID: {pid}")
            sys.exit(0)

        os.setsid()
        os.umask(0)

        pid = os.fork()
        if pid > 0:
            sys.exit(0)

        sys.stdout.flush()
        sys.stderr.flush()
        with open(os.devnull, 'r') as stdin, open(os.devnull, 'a') as stdout, open(os.devnull, 'a') as stderr:
            os.dup2(stdin.fileno(), sys.stdin.fileno())
            os.dup2(stdout.fileno(), sys.stdout.fileno())
            os.dup2(stderr.fileno(), sys.stderr.fileno())

        run_detector()


def stop():
    """Stops the background tool."""
    if not os.path.exists(PID_FILE):
        print("Not running.")
        return

    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())

        process = psutil.Process(pid)
        process.terminate()
        process.wait(timeout=3)
        print("Stopped successfully.")
    except (psutil.NoSuchProcess, ValueError):
        print("Process already dead.")
    except Exception as e:
        print(f"Error stopping: {e}")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def status():
    """Check if running."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                print(f"spankurlaptop is RUNNING (PID: {pid})")
                return
        except Exception:
            pass
    print("spankurlaptop is NOT running.")


def uninstall():
    """Uninstall the tool and clean up files."""
    print("Uninstalling spankurlaptop...")

    if os.path.exists(PID_FILE):
        stop()

    if os.path.exists(PROFILE_FILE):
        os.remove(PROFILE_FILE)
        print(f"Removed {PROFILE_FILE}")

    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    print("Cleanup complete.")
    print("To fully uninstall, run: pip uninstall spankurlaptop")


# --- AUDIO & DETECTION LOGIC ---

class SpankDetector:
    def __init__(self, mode="run", calib_target=100):
        self.mode = mode
        self.sounds = []

        if mode == "run":
            self.load_sounds()
            if os.path.exists(PROFILE_FILE):
                data = np.load(PROFILE_FILE)
                self.profile = data['spectrum']
                self.calibrated_rms = float(data['rms'])
                print(f"Loaded saved spank profile. Baseline Spank Vol: {self.calibrated_rms:.4f}")
            else:
                self.profile = None
                self.calibrated_rms = 0.0
                print("No spank_profile.npz found. Running in generic volume mode. Consider running 'calibrate' first.")

        # Detection state
        self.history = []
        self.history_len = int(SAMPLE_RATE / BLOCK_SIZE * 2)  # 2 seconds of history
        self.cooldown = 0
        self.cool_down_frames = int(SAMPLE_RATE / BLOCK_SIZE * 0.5)  # 0.5 seconds cooldown

        # Calibration state
        self.calibrating = False
        self.calib_count = 0
        self.calib_spectra = []
        self.calib_rmss = []
        self.calib_target = calib_target  # Now configurable!

    def load_sounds(self):
        """Loads sounds directly from memory using zipfile for 0 latency playback."""
        mixer.pre_init(SAMPLE_RATE, -16, 2, BLOCK_SIZE)
        mixer.init()

        audio_zip = _get_audio_zip_path()

        if not audio_zip or not os.path.exists(audio_zip):
            print(f"Warning: audio.zip not found at '{audio_zip}'. Audio reactions won't play.")
            print("Tip: Try reinstalling with: pip install --force-reinstall .")
            return

        try:
            with zipfile.ZipFile(audio_zip, 'r') as zf:
                mp3_files = [f for f in zf.namelist() if f.lower().endswith('.mp3')]
                mp3_files.sort()

                if not mp3_files:
                    print("Warning: No .mp3 files found inside audio.zip!")
                    return

                for file in mp3_files:
                    data = zf.read(file)
                    sound = mixer.Sound(io.BytesIO(data))
                    self.sounds.append(sound)

            print(f"Loaded {len(self.sounds)} sounds ready to scream!")
        except Exception as e:
            print(f"Error loading sounds: {e}")

    def get_spectrum(self, audio_data):
        """Returns the normalized magnitude spectrum of the audio data block."""
        spectrum = np.abs(np.fft.rfft(audio_data[:, 0]))
        norm = np.linalg.norm(spectrum)
        if norm > 0:
            spectrum = spectrum / norm
        return spectrum

    def audio_callback(self, indata, frames, time_info, status):
        """Called for every block of audio to detect spikes immediately."""
        if hasattr(self, 'stop_flag') and self.stop_flag:
            raise sd.CallbackStop()

        if self.cooldown > 0:
            self.cooldown -= 1

        rms = np.sqrt(np.mean(indata**2))

        if self.cooldown <= 0 and len(self.history) == self.history_len:
            avg_baseline = np.mean(self.history)

            # Check for a sharp spike
            if rms > avg_baseline * 5.0 and rms > 0.01:

                # Crest factor (peak to rms ratio) - impulse like a slap is very sharp (> 3.5)
                peak = np.max(np.abs(indata))
                crest_factor = peak / (rms + 1e-10)

                if crest_factor > 3.0:
                    spectrum = self.get_spectrum(indata)

                    if self.mode == "calibrate" and self.calibrating:
                        self.calib_spectra.append(spectrum)
                        self.calib_rmss.append(rms)
                        self.calib_count += 1
                        print(f"[{self.calib_count}/{self.calib_target}] Spank registered! (Intensity: {rms:.4f})")
                        self.cooldown = self.cool_down_frames * 2  # 1 second cooldown

                        if self.calib_count >= self.calib_target:
                            self.stop_flag = True  # Auto stop when done

                    elif self.mode == "run":
                        intensity = min(1.0, max(0.0, (rms - 0.01) / 0.3))

                        if self.profile is not None:
                            similarity = np.dot(spectrum, self.profile)

                            # Lowered threshold from 0.92 to 0.82 for more reliability on laptop mics
                            # Lowered volume gate from 0.60 to 0.40
                            if (similarity > 0.82 and rms > (self.calibrated_rms * 0.40)) or (rms > self.calibrated_rms * 1.5):
                                self.play_reaction(intensity)
                                self.cooldown = self.cool_down_frames
                        else:
                            self.play_reaction(intensity)
                            self.cooldown = self.cool_down_frames

        # Continually update history
        self.history.append(rms)
        if len(self.history) > self.history_len:
            self.history.pop(0)

    def play_reaction(self, intensity):
        """Plays a sound scaled to the spank intensity."""
        if not self.sounds:
            print("[DEBUG] No sounds loaded — nothing to play!")
            return

        total_sounds = len(self.sounds)
        bucket_size = max(1, total_sounds // 5)
        bucket_index = int(intensity * 4.99)  # 0 to 4

        start_idx = bucket_index * bucket_size
        end_idx = min(total_sounds, start_idx + bucket_size)

        if start_idx >= end_idx:
            sound_idx = total_sounds - 1
        else:
            sound_idx = random.randint(start_idx, end_idx - 1)

        # Log playback for debugging
        log_path = os.path.join(os.path.expanduser("~"), "spankurlaptop_debug.log")
        with open(log_path, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] Playing sound {sound_idx} (Intensity: {intensity:.2f})\n")

        self.sounds[sound_idx].play()

    def start_listening(self):
        print("Listening for spanks in the background...")
        self.stop_flag = False
        with sd.InputStream(callback=self.audio_callback, channels=1, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE):
            while not self.stop_flag:
                time.sleep(0.1)

    def run_calibration(self):
        print("=" * 50)
        print("CALIBRATION MODE")
        print("=" * 50)
        print(f"I need to learn your laptop's unique spank sound profile.")
        print(f"Please loudly spank your laptop {self.calib_target} times, pausing slightly between each.")
        print("Listening started... Spank now!")

        self.stop_flag = False
        self.calibrating = True

        self.history = [0.001] * self.history_len

        try:
            with sd.InputStream(callback=self.audio_callback, channels=1, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE):
                while not self.stop_flag:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nCalibration manually cancelled.")
            return

        if len(self.calib_spectra) > 0:
            avg_spectrum = np.mean(self.calib_spectra, axis=0)
            avg_spectrum = avg_spectrum / (np.linalg.norm(avg_spectrum) + 1e-10)
            avg_rms = float(np.mean(self.calib_rmss))

            np.savez(PROFILE_FILE, spectrum=avg_spectrum, rms=avg_rms)

            # Delete old .npy if exists
            old_npy = PROFILE_FILE.replace(".npz", ".npy")
            if os.path.exists(old_npy):
                os.remove(old_npy)

            print("=" * 50)
            print(f"Calibration complete! Saved signature and volume thresholds to {PROFILE_FILE}.")
            print(f"Average spank volume measured: {avg_rms:.4f}")
            print("Now run: spankurlaptop start")
        else:
            print("No spanks detected during calibration. Try again!")


def run_detector():
    """Main execution of the background task."""
    try:
        detector = SpankDetector(mode="run")
        detector.start_listening()
    except Exception as e:
        log_path = os.path.join(os.path.expanduser("~"), "spankurlaptop_error.log")
        with open(log_path, "w") as f:
            f.write(str(e))


def main():
    parser = argparse.ArgumentParser(description="SpankUrLaptop CLI Tool")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start", help="Start spankurlaptop in the background")
    subparsers.add_parser("stop", help="Stop the background process")
    subparsers.add_parser("status", help="Check if spankurlaptop is running")
    subparsers.add_parser("run", help="Run in foreground (used internally)")
    subparsers.add_parser("uninstall", help="Uninstall and clean up files")
    subparsers.add_parser("test-audio", help="Instantly play a random moan to test volume")

    calib_parser = subparsers.add_parser("calibrate", help="Calibrate spank detection")
    calib_parser.add_argument(
        "--count", type=int, default=100,
        help="Number of spanks to calibrate with (default: 100). Example: --count 20"
    )

    args = parser.parse_args()

    if args.command == "start":
        daemonize()
    elif args.command == "stop":
        stop()
    elif args.command == "status":
        status()
    elif args.command == "calibrate":
        count = args.count
        print(f"Calibrating with {count} spanks...")
        detector = SpankDetector(mode="calibrate", calib_target=count)
        detector.run_calibration()
    elif args.command == "run":
        run_detector()
    elif args.command == "uninstall":
        uninstall()
    elif args.command == "test-audio":
        print("Testing audio output...")
        detector = SpankDetector(mode="run")
        if not detector.sounds:
            print("Error: No sounds loaded.")
        else:
            print(f"Playing random sound from {len(detector.sounds)} available.")
            detector.play_reaction(random.random())
            time.sleep(2) # Give it time to play
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
