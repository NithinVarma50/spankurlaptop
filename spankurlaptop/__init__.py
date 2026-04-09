import os
import sys
import argparse
import subprocess
import json
import zipfile
import io
import random
import time
import math
import psutil
import threading

try:
    import numpy as np  # type: ignore
    import sounddevice as sd  # type: ignore
    from pygame import mixer  # type: ignore
except ImportError:
    print("Dependencies missing! Please run: pip install -r requirements.txt")
    sys.exit(1)

# Global settings used by GUI and detectors
global_settings = {
    "is_enabled": True,
    "global_volume": 1.0,
    "global_sensitivity": 1.0
}

# --- Locate audio.zip reliably regardless of install method ---
def _get_audio_zip_path():
    try:
        from importlib.resources import files
        ref = files("spankurlaptop").joinpath("audio.zip")
        path = str(ref)
        if os.path.exists(path):
            return path
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp.write(ref.read_bytes())
        tmp.close()
        return tmp.name
    except Exception:
        pass

    try:
        import pkg_resources  # type: ignore
        return pkg_resources.resource_filename("spankurlaptop", "audio.zip")
    except Exception:
        pass

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio.zip")


PID_FILE = os.path.join(os.path.expanduser("~"), ".spankurlaptop.pid")
PROFILE_FILE = os.path.join(os.path.expanduser("~"), ".spankurlaptop_profile.npz")
SAMPLE_RATE = 44100
BLOCK_SIZE = 256  

def daemonize():
    if os.path.exists(PID_FILE):
        print("Tool is already running. Try 'stop' first.")
        return

    print("Starting spankurlaptop in background...")
    if sys.platform == "win32":
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
        print("Press Ctrl+5 anytime to open the setup menu.")
    else:
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


class BaseDetector:
    def __init__(self):
        self.sounds = []
        self.stop_flag = False

    def load_sounds(self):
        try:
            mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=256)
        except Exception:
            mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
            mixer.init()

        audio_zip = _get_audio_zip_path()
        if not audio_zip or not os.path.exists(audio_zip):
            print(f"Warning: audio.zip not found at '{audio_zip}'. Audio reactions won't play.")
            return

        try:
            with zipfile.ZipFile(audio_zip, 'r') as zf:
                mp3_files = [f for f in zf.namelist() if f.lower().endswith('.mp3')]
                mp3_files.sort()
                for file in mp3_files:
                    data = zf.read(file)
                    sound = mixer.Sound(io.BytesIO(data))
                    self.sounds.append(sound)
        except Exception as e:
            print(f"Error loading sounds: {e}")

    def play_reaction(self, base_volume):
        if not global_settings["is_enabled"]:
            return
        if not self.sounds:
            return

        total_sounds = len(self.sounds)
        sound_idx = random.randint(0, total_sounds - 1)
        sound = self.sounds[sound_idx]
        
        final_vol = min(1.0, base_volume * global_settings["global_volume"])
        sound.set_volume(final_vol)
        sound.play()


class AccelerometerDetector(BaseDetector):
    def __init__(self, mode="run"):
        super().__init__()
        self.mode = mode
        self.cooldown = 0
        from winrt.windows.devices.sensors import Accelerometer
        self.sensor = Accelerometer.get_default()
        self.last_mag = 1.0
        if mode == "run":
            self.load_sounds()

    def _on_reading_changed(self, sender, args):
        if self.stop_flag or not global_settings["is_enabled"]:
            return

        reading = args.reading
        mag = math.sqrt(reading.acceleration_x**2 + reading.acceleration_y**2 + reading.acceleration_z**2)
        spike = abs(mag - self.last_mag)
        self.last_mag = mag

        if self.cooldown > 0:
            self.cooldown -= 1
            return
            
        sensitivity = global_settings["global_sensitivity"]
        threshold = 0.5 / max(0.1, sensitivity)

        if spike > threshold:
            intensity = min(1.0, max(0.2, spike / 2.0))
            self.play_reaction(intensity)
            self.cooldown = 10 

    def start_listening(self):
        self.stop_flag = False
        if not self.sensor:
            return
        
        try:
            self.sensor.report_interval = self.sensor.minimum_report_interval
        except:
            pass

        token = self.sensor.add_reading_changed(self._on_reading_changed)
        while not self.stop_flag:
            time.sleep(0.1)
        self.sensor.remove_reading_changed(token)


class SpankDetector(BaseDetector):
    def __init__(self, mode="run", calib_target=100):
        super().__init__()
        self.mode = mode
        if mode == "run":
            self.load_sounds()
            if os.path.exists(PROFILE_FILE):
                data = np.load(PROFILE_FILE)
                self.profile = data['spectrum']
                self.calibrated_rms = float(data['rms'])
            else:
                self.profile = None
                self.calibrated_rms = 0.0

        self.history = []
        self.history_len = int(SAMPLE_RATE / BLOCK_SIZE * 2)
        self.cooldown = 0
        self.cool_down_frames = int(SAMPLE_RATE / BLOCK_SIZE * 0.5)

        self.calibrating = False
        self.calib_count = 0
        self.calib_spectra = []
        self.calib_rmss = []
        self.calib_target = calib_target 

    def get_spectrum(self, audio_data):
        spectrum = np.abs(np.fft.rfft(audio_data[:, 0]))
        norm = np.linalg.norm(spectrum)
        if norm > 0:
            spectrum = spectrum / norm
        return spectrum

    def audio_callback(self, indata, frames, time_info, status):
        if self.stop_flag:
            raise sd.CallbackStop()
        if not global_settings["is_enabled"] and self.mode == "run":
            return

        if self.cooldown > 0:
            self.cooldown -= 1

        rms = np.sqrt(np.mean(indata**2))

        if self.cooldown <= 0 and len(self.history) == self.history_len:
            avg_baseline = np.mean(self.history)

            sensitivity = global_settings["global_sensitivity"]
            sens_multiplier = max(0.1, sensitivity)

            if rms > (avg_baseline * 5.0) / sens_multiplier and rms > 0.01:
                peak = np.max(np.abs(indata))
                crest_factor = peak / (rms + 1e-10)

                if crest_factor > 3.0:
                    spectrum = self.get_spectrum(indata)

                    if self.mode == "calibrate" and self.calibrating:
                        self.calib_spectra.append(spectrum)
                        self.calib_rmss.append(rms)
                        self.calib_count += 1
                        print(f"[{self.calib_count}/{self.calib_target}] Spank registered! (Intensity: {rms:.4f})")
                        self.cooldown = self.cool_down_frames * 2  

                        if self.calib_count >= self.calib_target:
                            self.stop_flag = True  

                    elif self.mode == "run":
                        if self.profile is not None:
                            similarity = np.dot(spectrum, self.profile)
                            if (similarity > 0.82 and rms > (self.calibrated_rms * 0.40) / sens_multiplier) or (rms > self.calibrated_rms * 1.5):
                                ratio = rms / (self.calibrated_rms + 1e-10)
                                volume = min(1.0, max(0.2, ratio / 1.25))
                                self.play_reaction(volume)
                                self.cooldown = self.cool_down_frames
                        else:
                            intensity = min(1.0, max(0.2, (rms - 0.01) / 0.10))
                            self.play_reaction(intensity)
                            self.cooldown = self.cool_down_frames

        self.history.append(rms)
        if len(self.history) > self.history_len:
            self.history.pop(0)

    def start_listening(self):
        self.stop_flag = False
        with sd.InputStream(callback=self.audio_callback, channels=1, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE):
            while not self.stop_flag:
                time.sleep(0.1)

    def run_calibration(self):
        print("=" * 50)
        print("CALIBRATION MODE")
        print("=" * 50)
        print(f"Please loudly spank your laptop {self.calib_target} times, pausing slightly between each.")
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
            old_npy = PROFILE_FILE.replace(".npz", ".npy")
            if os.path.exists(old_npy):
                os.remove(old_npy)
            print("=" * 50)
            print(f"Calibration complete! Saved {PROFILE_FILE}.")
        else:
            print("No spanks detected.")


def run_detector():
    """Main execution of the background task."""
    has_accel = False
    if sys.platform == "win32":
        try:
            import winrt.windows.devices.sensors as sensors
            has_accel = sensors.Accelerometer.get_default() is not None
        except Exception:
            has_accel = False

    global current_detector
    if has_accel:
        current_detector = AccelerometerDetector(mode="run")
        detector_type_str = "Accelerometer"
    else:
        current_detector = SpankDetector(mode="run")
        detector_type_str = "Microphone"

    def detector_loop():
        try:
            current_detector.start_listening()
        except Exception as e:
            log_path = os.path.join(os.path.expanduser("~"), "spankurlaptop_error.log")
            with open(log_path, "w") as f:
                f.write(str(e))

    thread = threading.Thread(target=detector_loop, daemon=True)
    thread.start()

    import tkinter as tk
    try:
        import keyboard
    except ImportError:
        keyboard = None

    root = tk.Tk()
    root.title("SpankUrLaptop Control Panel")
    root.geometry("320x350")
    root.resizable(False, False)
    root.withdraw() 
    
    # Store settings correctly inside tkinter
    def apply_settings():
        global_settings["is_enabled"] = enable_var.get()
        global_settings["global_volume"] = float(vol_scale.get())
        global_settings["global_sensitivity"] = float(sens_scale.get())

    def toggle_window():
        if root.state() == "withdrawn":
            root.deiconify()
            root.lift()
            root.attributes('-topmost', True)
            root.attributes('-topmost', False)
        else:
            root.withdraw()

    if keyboard:
        try:
            keyboard.add_hotkey('ctrl+5', lambda: root.after(0, toggle_window))
        except:
            pass

    def on_closing():
        root.withdraw()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # UI Layout
    tk.Label(root, text="👋 SpankUrLaptop UI", font=("Arial", 16, "bold")).pack(pady=(15, 5))
    tk.Label(root, text=f"Currently using: {detector_type_str}", fg="blue", font=("Arial", 10)).pack(pady=(0, 10))

    enable_var = tk.BooleanVar(value=True)
    tk.Checkbutton(root, text="Enabled (On/Off)", font=("Arial", 11), variable=enable_var, command=apply_settings).pack(pady=5)

    tk.Label(root, text="Master Audio Volume", font=("Arial", 10)).pack(pady=(10, 0))
    vol_scale = tk.Scale(root, from_=0.0, to_=2.0, resolution=0.1, orient="horizontal", command=lambda x: apply_settings(), length=200)
    vol_scale.set(1.0)
    vol_scale.pack()

    tk.Label(root, text="Spank Sensitivity", font=("Arial", 10)).pack(pady=(10, 0))
    sens_scale = tk.Scale(root, from_=0.1, to_=3.0, resolution=0.1, orient="horizontal", command=lambda x: apply_settings(), length=200)
    sens_scale.set(1.0)
    sens_scale.pack()

    def test_scream():
        if current_detector:
            current_detector.play_reaction(1.0)
            
    tk.Button(root, text="Test Scream 🔊", command=test_scream, bg="#ff4c4c", fg="white", font=("Arial", 12, "bold"), padx=10, pady=5).pack(pady=20)

    # Let the GUI take main thread!
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser(description="SpankUrLaptop CLI Tool")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("start", help="Start spankurlaptop in the background")
    subparsers.add_parser("stop", help="Stop the background process")
    subparsers.add_parser("status", help="Check if spankurlaptop is running")
    subparsers.add_parser("run", help="Run in foreground")
    subparsers.add_parser("uninstall", help="Uninstall and clean up files")
    subparsers.add_parser("test-audio", help="Play a random moan to test volume")

    calib_parser = subparsers.add_parser("calibrate", help="Calibrate spank detection")
    calib_parser.add_argument("--count", type=int, default=100)

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
        detector = BaseDetector()
        detector.load_sounds()
        if not detector.sounds:
            print("Error: No sounds loaded.")
        else:
            print(f"Playing random sound from {len(detector.sounds)} available.")
            detector.play_reaction(random.random())
            time.sleep(2)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
