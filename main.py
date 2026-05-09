import time
import signal
import sys
import threading
from sensors.camera import CameraSystem
from sensors.ultrasonic import UltrasonicSensor
from sensors.sos_button import SOSButton
from actuators.buzzer import Buzzer
from server import DualServer

class SmartStick:
    def __init__(self):
        print("\n--- Smart Stick Backend Starting ---")
        print("[System] Mode: Android Remote Inference")
        
        # Initialize Hardware components
        self.camera = CameraSystem()
        self.ultrasonic = UltrasonicSensor()
        self.buzzer = Buzzer()
        
        # Initialize SOS Button with callback
        self.sos_button = SOSButton(pin=17, callback=self.trigger_sos)
        
        # Initialize Networking (Dual Server)
        self.server = DualServer(self.camera, self.ultrasonic)
        
        self.running = True

    def trigger_sos(self):
        """Callback triggered by the physical SOS button."""
        # Use server's broadcast mechanism to notify Android app
        payload = {
            "event": "SOS",
            "timestamp": time.time()
        }
        self.server.broadcast_event(payload)

    def start(self):
        # 1. Start Camera capture thread
        self.camera.start()
        
        # 2. Start Buzzer background thread
        self.buzzer.start()
        
        # 3. Start SOS Button monitor
        self.sos_button.start()
        
        # 4. Start Dual Server (Port 5000: Sensors, Port 5001: MJPEG)
        self.server.start()
        
        print("[System] All services started successfully.")
        print("[System] Main safety loop running. Press Ctrl+C to exit.")
        
        try:
            while self.running:
                # Local Safety Logic:
                # The Pi reads the sensor and controls the buzzer locally
                # for instant feedback, regardless of WiFi/App latency.
                distance = self.ultrasonic.get_distance()
                
                # Update buzzer frequency based on distance
                self.buzzer.set_distance(distance)
                
                # Simple CLI monitor
                print(f"[Status] Dist: {distance:5.1f}cm | Buzzer: {'FAST' if distance < 30 else 'SLOW' if distance < 100 else 'OFF'}", end="\r")
                
                time.sleep(0.05) # 20Hz local safety check
                
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            print(f"\n[System] Runtime Error: {e}")
            self.stop()

    def stop(self):
        print("\n[System] Shutting down...")
        self.running = False
        
        # Graceful cleanup
        self.server.stop()
        self.camera.stop()
        self.buzzer.cleanup()
        self.ultrasonic.cleanup()
        self.sos_button.cleanup()
        
        print("[System] Cleanup complete. Goodbye.")
        sys.exit(0)

if __name__ == "__main__":
    stick = SmartStick()
    stick.start()
