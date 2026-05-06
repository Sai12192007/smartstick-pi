import os
import requests
import subprocess
import sys

def install_dependencies():
    print("[*] Installing dependencies...")
    packages = ["opencv-python", "numpy", "imutils", "requests"]
    
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
        print("[*] Raspberry Pi detected. Adding RPi.GPIO and picamera2...")
        packages.extend(["RPi.GPIO"])
        # picamera2 is often pre-installed or needs specific libcamera setup
        # but we'll try to install the wrapper if possible
    
    for package in packages:
        print(f"[*] Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def download_models():
    print("[*] Downloading MobileNet SSD models...")
    model_dir = "models"
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    files = {
        "deploy.prototxt": "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/deploy.prototxt",
        "mobilenet.caffemodel": "https://github.com/chuanqi305/MobileNet-SSD/raw/master/mobilenet_iter_73000.caffemodel"
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
