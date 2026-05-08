import cv2
import numpy as np
import threading
import time

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("[Camera] WARNING: Picamera2 not found.")

class CameraSystem:
    def __init__(self):
        self.picam2 = None
        self.latest_jpeg = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        # Initialize Picamera2 instance
        if PICAMERA2_AVAILABLE:
            try:
                self.picam2 = Picamera2()
                print("[Camera] Picamera2 initialized for streaming")
            except Exception as e:
                print(f"[Camera] ERROR: Could not initialize Picamera2: {e}")

    def start(self):
        if not self.picam2:
            print("[Camera] ERROR: Camera not initialized")
            return
        
        try:
            # Configure camera for optimal streaming (640x480)
            config = self.picam2.create_video_configuration(main={"size": (640, 480), "format": "BGR888"})
            self.picam2.configure(config)
            self.picam2.start()
            print("[Camera] Picamera2 started (Streaming Mode)")
            
            self.running = True
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
        except Exception as e:
            print(f"[Camera] ERROR: Failed to start camera: {e}")

    def _update(self):
        """Threaded loop for capturing and encoding frames as JPEG."""
        while self.running:
            try:
                frame = self.picam2.capture_array()
                if frame is None:
                    continue
                
                if frame.shape[2] == 4:
                    frame = frame[:, :, :3]
                
                # Encode frame to JPEG for transmission
                # Quality 60 is a good balance for Pi Zero 2 W
                success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                if success:
                    with self.lock:
                        self.latest_jpeg = buffer.tobytes()
                
            except Exception as e:
                print(f"[Camera] Capture/Encode Error: {e}")
            
            # Target ~10-15 FPS to avoid saturating Zero 2 W CPU/Network
            time.sleep(0.06)

    def get_jpeg_frame(self):
        """Returns the latest JPEG encoded frame as bytes."""
        with self.lock:
            return self.latest_jpeg

    def get_latest_detection(self):
        """Deprecated: Detection now happens on Android app."""
        return {"object": "none", "confidence": 0, "box": None}

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
                print("[Camera] Stopped")
            except:
                pass
