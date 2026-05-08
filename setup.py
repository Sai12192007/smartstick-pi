import os
import requests
import subprocess
import sys

def install_dependencies():
    print("[*] Installing system dependencies (requires sudo)...")
    try:
        # Install libraries needed by OpenCV and TFLite
        subprocess.check_call(["sudo", "apt-get", "update"])
        subprocess.check_call(["sudo", "apt-get", "install", "-y", 
                             "libopenblas-dev", "libatlas-base-dev", "liblapack-dev",
                             "libjasper-dev", "libqtgui4", "libqt4-test"])
    except Exception as e:
        print(f"[!] Warning: Could not install system dependencies via apt: {e}")
        print("[!] Please run: sudo apt install libopenblas-dev libatlas-base-dev")

    print("[*] Installing Python dependencies...")
    # Try ai-edge-litert first as it's the newer version of tflite-runtime
    packages = ["opencv-python", "numpy", "imutils", "requests", "ai-edge-litert"]
    
    # Check if we are on a Raspberry Pi
    is_pi = False
    try:
        if os.path.exists('/proc/device-tree/model'):
            with open('/proc/device-tree/model', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    is_pi = True
    except:
        pass

    pip_cmd = [sys.executable, "-m", "pip", "install"]
    if is_pi:
        print("[*] Raspberry Pi detected. Adding RPi.GPIO and using --break-system-packages...")
        packages.extend(["RPi.GPIO"])
        pip_cmd.append("--break-system-packages")
    
    for package in packages:
        print(f"[*] Installing {package}...")
        try:
            subprocess.check_call(pip_cmd + [package])
        except subprocess.CalledProcessError:
            if package == "ai-edge-litert":
                print("[*] ai-edge-litert failed, trying tflite-runtime...")
                try:
                    subprocess.check_call(pip_cmd + ["tflite-runtime"])
                except:
                    print("[!] Warning: Failed to install TFLite. You may need to install it manually.")
            else:
                print(f"[!] Warning: Failed to install {package}.")

def download_models():
    print("[*] Downloading EfficientDet-Lite0 TFLite models...")
    model_dir = "models"
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    files = {
        "efficientdet_lite0.tflite": "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/latest/efficientdet_lite0.tflite",
        "labels.txt": "https://raw.githubusercontent.com/amikelive/coco-labels/master/coco-labels-2014_2017.txt"
    }

    for filename, url in files.items():
        path = os.path.join(model_dir, filename)
        if not os.path.exists(path):
            print(f"[*] Downloading {filename}...")
            try:
                response = requests.get(url, stream=True)
                with open(path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"[+] Downloaded {filename}")
            except Exception as e:
                print(f"[!] Failed to download {filename}: {e}")
        else:
            print(f"[*] {filename} already exists.")

if __name__ == "__main__":
    try:
        install_dependencies()
    except Exception as e:
        print(f"[!] Dependency install error: {e}")
    
    # Always try to download models
    download_models()
    print("[+] Setup complete!")
