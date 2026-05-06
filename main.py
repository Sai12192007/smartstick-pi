import time
import signal
import sys
from sensors.camera import CameraSystem
from sensors.ultrasonic import UltrasonicSensor
from actuators.buzzer import Buzzer
from server import SocketServer
from utils.logic import get_direction, format_data

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
                
                # 2. Get Object Detection
                detection = self.camera.get_latest_detection()
                obj_name = detection["object"]
                box = detection["box"]
                frame_width = detection.get("frame_width", 300)
                
                # 3. Determine Direction
                direction = get_direction(box, frame_width)
                
                # 4. Apply Buzzer Logic
                self.buzzer.set_distance(distance)
                
                # 5. Format and Send Data
                message = format_data(obj_name, distance, direction)
                sent = self.server.send_data(message)
                
                # Log status
                print(f"[Status] Obj: {obj_name:7} | Dist: {distance:5}cm | Dir: {direction:7} | Socket: {'OK' if sent else 'Wait'}")
                
                # Sleep to maintain frequency (1-2 seconds as requested)
                time.sleep(1.0)
                
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
