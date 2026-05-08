import cv2
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

        if PICAMERA2_AVAILABLE:
            try:
                self.picam2 = Picamera2()
                print("[Camera] Picamera2 initialized for MJPEG streaming")
            except Exception as e:
                print(f"[Camera] ERROR: Could not initialize Picamera2: {e}")

    def start(self):
        if not self.picam2:
            return
        
        try:
            config = self.picam2.create_video_configuration(main={"size": (640, 480), "format": "BGR888"})
            self.picam2.configure(config)
            self.picam2.start()
            print("[Camera] Picamera2 started")
            
            self.running = True
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
        except Exception as e:
            print(f"[Camera] ERROR: Failed to start camera: {e}")

    def _update(self):
        while self.running:
            try:
                frame = self.picam2.capture_array()
                if frame is not None:
                    if frame.shape[2] == 4:
                        frame = frame[:, :, :3]
                    
                    # Encode to JPEG for MJPEG stream
                    success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    if success:
                        with self.lock:
                            self.latest_jpeg = buffer.tobytes()
                
            except Exception as e:
                print(f"[Camera] Capture error: {e}")
            
            time.sleep(0.05) # ~20 FPS limit

    def get_jpeg(self):
        with self.lock:
            return self.latest_jpeg

    def generate_mjpeg(self):
        """Generator for Flask MJPEG stream."""
        while self.running:
            frame = self.get_jpeg()
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
