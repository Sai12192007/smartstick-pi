import os
import requests
import subprocess
import sys

def install_dependencies():
    print("[*] Installing system dependencies (requires sudo)...")
    try:
        # Install libraries needed by OpenCV and Camera
        subprocess.check_call(["sudo", "apt-get", "update"])
        subprocess.check_call(["sudo", "apt-get", "install", "-y", 
                             "libopenblas-dev", "libatlas-base-dev", "libgomp1"])
    except Exception as e:
        print(f"[!] Warning: Could not install system dependencies via apt: {e}")

    print("[*] Installing Python dependencies...")
    # Core dependencies for MJPEG streaming and sensor serving
    packages = ["opencv-python-headless", "numpy", "imutils", "requests", "Flask", "flask-cors"]
    
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
            print(f"[!] Warning: Failed to install {package}.")

def download_models():
    # No longer needed as AI is on the Android App
    pass

if __name__ == "__main__":
    try:
        install_dependencies()
    except Exception as e:
        print(f"[!] Dependency install error: {e}")
    
    print("[+] Setup complete!")
