import time
import signal
import sys
import json
import base64
from sensors.camera import CameraSystem
from sensors.ultrasonic import UltrasonicSensor
from actuators.buzzer import Buzzer
from server import SocketServer

class SmartStick:
    def __init__(self):
        print("--- Smart Stick System Starting ---")
        
        # Initialize components
        self.camera = CameraSystem()
        self.ultrasonic = UltrasonicSensor()
        self.buzzer = Buzzer()
        self.server = SocketServer()
        
        self.running = True

    def start(self):
        # Start background systems
        self.camera.start()
        self.buzzer.start()
        self.server.start()
        
        print("[System] Main loop running. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                # 1. Get Distance
                distance = self.ultrasonic.get_distance()
                
                # 2. Get JPEG Frame
                jpeg_frame = self.camera.get_jpeg_frame()
                frame_b64 = ""
                if jpeg_frame:
                    frame_b64 = base64.b64encode(jpeg_frame).decode('utf-8')
                
                # 3. Apply Buzzer Logic (Local for low-latency safety)
                self.buzzer.set_distance(distance)
                
                # 4. Construct Data Payload for Android App
                payload = {
                    "distance": int(distance),
                    "frame": frame_b64,
                    "timestamp": time.time()
                }
                
                # 5. Send Data
                message = json.dumps(payload) + "\n"
                sent = self.server.send_data(message)
                
                # Log status (truncated for readability)
                if sent:
                    print(f"[Stream] Sending Frame + Dist: {int(distance)}cm", end="\r")
                else:
                    print("[Stream] Waiting for client connection...", end="\r")
                
                # Frequency control (10 FPS for stability on Zero 2 W)
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        print("\n--- Shutting down ---")
        self.running = False
        self.camera.stop()
        self.buzzer.cleanup()
        self.server.stop()
        self.ultrasonic.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    stick = SmartStick()
    stick.start()
