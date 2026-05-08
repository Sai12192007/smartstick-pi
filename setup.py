import os
import requests
import subprocess
import sys

def install_dependencies():
    print("[*] Installing dependencies...")
    packages = ["opencv-python", "numpy", "imutils", "requests", "tflite-runtime"]
    
    # Check if we are on a Raspberry Pi
    is_pi = False
    try:
        if os.path.exists('/proc/device-tree/model'):
            with open('/proc/device-tree/model', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    is_pi = True
    except:
        pass

    if is_pi:
        print("[*] Raspberry Pi detected. Adding RPi.GPIO...")
        packages.extend(["RPi.GPIO"])
        print("[!] IMPORTANT: Picamera2 must be installed via system package manager:")
        print("[!] sudo apt update && sudo apt install python3-picamera2")
    
    for package in packages:
        print(f"[*] Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

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
            response = requests.get(url, stream=True)
            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"[+] Downloaded {filename}")
        else:
            print(f"[*] {filename} already exists.")

if __name__ == "__main__":
    install_dependencies()
    download_models()
    print("[+] Setup complete!")
