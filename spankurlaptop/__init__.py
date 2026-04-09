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

# Global variables
current_detector = None

global_settings = {
    "is_enabled": True,
    "global_volume": 1.0,
    "global_sensitivity": 1.0
}

default_settings = {
    "is_enabled": True,
    "global_volume": 1.0,
    "global_sensitivity": 1.0
}

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
        self.sensor = None
        try:
            import importlib
            _winrt_sensors = importlib.import_module("winrt.windows.devices.sensors")
            Accelerometer = _winrt_sensors.Accelerometer
            self.sensor = Accelerometer.get_default()
        except Exception:
            self.sensor = None
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


HTML_UI = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f7;
            color: #1d1d1f;
            margin: 0;
            padding: 30px;
            user-select: none;
            overflow: hidden;
        }
        h1 { font-size: 24px; font-weight: 600; text-align: center; margin-top: 10px; margin-bottom: 2px; }
        .subtitle { text-align: center; color: #86868b; font-size: 13px; margin-bottom: 25px; font-weight: 500;}
        .card {
            background: #ffffff;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
            margin-bottom: 15px;
        }
        .row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .row.last { margin-bottom: 0px; }
        
        .label-group { display: flex; flex-direction: column; }
        .label { font-size: 15px; font-weight: 500; }
        .sublabel { font-size: 12px; color: #86868b; margin-top: 2px;}

        /* Apple style Toggle */
        .switch { position: relative; display: inline-block; width: 50px; height: 30px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider-toggle {
            position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
            background-color: #e9e9ea; transition: .4s; border-radius: 30px;
        }
        .slider-toggle:before {
            position: absolute; content: ""; height: 26px; width: 26px; left: 2px; bottom: 2px;
            background-color: white; transition: .4s; border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        input:checked + .slider-toggle { background-color: #34c759; }
        input:checked + .slider-toggle:before { transform: translateX(20px); }

        /* Sliders */
        input[type=range] {
            -webkit-appearance: none; width: 100%; background: transparent; margin-top: 10px;
        }
        input[type=range]:focus { outline: none; }
        input[type=range]::-webkit-slider-runnable-track {
            width: 100%; height: 6px; cursor: pointer;
            background: #e9e9ea; border-radius: 3px;
        }
        input[type=range]::-webkit-slider-thumb {
            height: 20px; width: 20px; border-radius: 50%; background: #ffffff;
            cursor: pointer; -webkit-appearance: none; margin-top: -7px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2); border: 0.5px solid #d1d1d6;
        }
        
        .btn {
            appearance: none; background: #007aff; border: none; border-radius: 10px;
            color: #fff; font-size: 15px; font-weight: 600; padding: 12px; width: 100%;
            cursor: pointer; transition: background 0.2s;
        }
        .btn:hover { background: #006ce4; }
        .btn.outline {
            background: transparent; border: 1px solid #d1d1d6; color: #ff3b30; margin-top: 10px;
        }
        .btn.outline:hover { background: #fff0f0; }
    </style>
</head>
<body>
    <h1>SpankUrLaptop</h1>
    <div class="subtitle" id="sensor-status">Currently using: Loading...</div>

    <div class="card">
        <div class="row last">
            <div class="label-group">
                <span class="label">Enabled</span>
                <span class="sublabel">Toggle tool on or off</span>
            </div>
            <label class="switch">
                <input type="checkbox" id="toggle-enable" onchange="pywebview.api.set_enabled(this.checked)">
                <span class="slider-toggle"></span>
            </label>
        </div>
    </div>

    <div class="card">
        <div class="row last" style="flex-direction: column; align-items: flex-start;">
            <div class="label-group" style="width: 100%;">
                <div style="display:flex; justify-content: space-between;">
                    <span class="label">Master Volume</span>
                    <span class="label" id="val-vol" style="color:#007aff;">100%</span>
                </div>
            </div>
            <input type="range" id="slider-vol" min="0" max="2" step="0.1" value="1.0" 
                oninput="document.getElementById('val-vol').innerText = Math.round(this.value * 100) + '%'; pywebview.api.set_volume(this.value)">
        </div>
    </div>

    <div class="card">
        <div class="row last" style="flex-direction: column; align-items: flex-start;">
            <div class="label-group" style="width: 100%;">
                <div style="display:flex; justify-content: space-between;">
                    <span class="label">Slap Sensitivity</span>
                    <span class="label" id="val-sens" style="color:#007aff;">1.0</span>
                </div>
            </div>
            <input type="range" id="slider-sens" min="0.1" max="3" step="0.1" value="1.0" 
                oninput="document.getElementById('val-sens').innerText = this.value; pywebview.api.set_sensitivity(this.value)">
        </div>
    </div>

    <button class="btn" onclick="pywebview.api.test_scream()">Test Scream 🔊</button>
    <button class="btn outline" onclick="resetDefaults()">Reset to Defaults</button>

    <script>
        function updateUI(state) {
            document.getElementById('sensor-status').innerText = "Currently using: " + state.sensor;
            document.getElementById('toggle-enable').checked = state.is_enabled;
            
            let vol = state.global_volume;
            document.getElementById('slider-vol').value = vol;
            document.getElementById('val-vol').innerText = Math.round(vol * 100) + '%';
            
            let sens = state.global_sensitivity;
            document.getElementById('slider-sens').value = sens;
            document.getElementById('val-sens').innerText = sens;
        }

        function resetDefaults() {
            pywebview.api.reset_settings().then(updateUI);
        }

        window.addEventListener('pywebviewready', function() {
            pywebview.api.load_state().then(updateUI);
        });
    </script>
</body>
</html>
"""

is_window_hidden = True

class Api:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def load_state(self):
        global current_detector
        sensor_name = getattr(current_detector, "mode_str", "Unknown") if current_detector else "Unknown"
        return {
            "sensor": sensor_name,
            "is_enabled": global_settings["is_enabled"],
            "global_volume": global_settings["global_volume"],
            "global_sensitivity": global_settings["global_sensitivity"]
        }

    def set_enabled(self, state):
        global_settings["is_enabled"] = bool(state)

    def set_volume(self, value):
        global_settings["global_volume"] = float(value)

    def set_sensitivity(self, value):
        global_settings["global_sensitivity"] = float(value)

    def test_scream(self):
        global current_detector
        if current_detector:
            current_detector.play_reaction(1.0)

    def reset_settings(self):
        global_settings.update(default_settings)
        return self.load_state()

    def hide_window(self):
        if self._window:
            global is_window_hidden
            self._window.hide()
            is_window_hidden = True

def run_detector():
    """Main execution of the background task."""
    has_accel = False
    if sys.platform == "win32":
        try:
            import importlib
            _winrt_sensors = importlib.import_module("winrt.windows.devices.sensors")
            has_accel = _winrt_sensors.Accelerometer.get_default() is not None
        except Exception:
            has_accel = False

    global current_detector
    if has_accel:
        current_detector = AccelerometerDetector(mode="run")
        current_detector.mode_str = "Accelerometer"
    else:
        current_detector = SpankDetector(mode="run")
        current_detector.mode_str = "Microphone"

    def detector_loop():
        global current_detector
        try:
            current_detector.start_listening()
        except Exception as e:
            log_path = os.path.join(os.path.expanduser("~"), "spankurlaptop_error.log")
            with open(log_path, "w") as f:
                f.write(str(e))

    thread = threading.Thread(target=detector_loop, daemon=True)
    thread.start()

    try:
        import importlib
        webview = importlib.import_module("webview")
    except ImportError:
        print("Error: 'pywebview' not installed correctly.")
        return

    try:
        import keyboard  # type: ignore
    except ImportError:
        keyboard = None

    api = Api()
    
    # We create the window hidden initially so that it only pops on Ctrl+5
    window = webview.create_window(
        title='SpankUrLaptop Settings', 
        html=HTML_UI, 
        js_api=api,
        width=400, 
        height=620,
        resizable=False,
        hidden=True,
        on_top=True
    )
    api.set_window(window)

    def on_closing():
        global is_window_hidden
        window.hide()
        is_window_hidden = True
        return False # Prevent actual closing

    window.events.closing += on_closing

    def toggle_window():
        global is_window_hidden
        if is_window_hidden:
            window.show()
            is_window_hidden = False
        else:
            window.hide()
            is_window_hidden = True

    if keyboard:
        try:
            keyboard.add_hotkey('ctrl+5', toggle_window)
        except:
            pass

    try:
        webview.start(debug=False)
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
