import cv2
import numpy as np
import threading
import os
import time

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("[Camera] WARNING: Picamera2 not found. Camera will not work on non-Pi systems.")

class CameraSystem:
    def __init__(self, model_path="models/mobilenet.caffemodel", prototxt_path="models/deploy.prototxt"):
        self.model_path = model_path
        self.prototxt_path = prototxt_path
        
        # VOC Class labels
        self.CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
                        "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
                        "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
                        "sofa", "train", "tvmonitor"]
        
        # Filter for important objects
        self.IMPORTANT_CLASSES = ["person", "car", "chair", "bottle", "bus", "dog", "cat"]
        
        self.net = None
        self.picam2 = None
        self.latest_frame = None
        self.current_detection = {"object": "none", "confidence": 0, "box": None}
        self.running = False
        self.thread = None

        # Initialize ML model
        if os.path.exists(self.model_path) and os.path.exists(self.prototxt_path):
            try:
                self.net = cv2.dnn.readNetFromCaffe(self.prototxt_path, self.model_path)
                print("[Camera] ML Model loaded successfully")
            except Exception as e:
                print(f"[Camera] ERROR: Failed to load ML model: {e}")
        else:
            print("[Camera] ERROR: Model files not found. Run setup.py first.")

        # Initialize Picamera2 instance
        if PICAMERA2_AVAILABLE:
            try:
                self.picam2 = Picamera2()
                print("[Camera] Picamera2 initialized")
            except Exception as e:
                print(f"[Camera] ERROR: Could not initialize Picamera2: {e}")
        else:
            print("[Camera] ERROR: Picamera2 is required for this system.")

    def start(self):
        if not self.picam2:
            print("[Camera] ERROR: Cannot start, camera not initialized")
            return
        
        try:
            # Configure camera: 640x480 resolution with BGR888 format
            config = self.picam2.create_video_configuration(main={
                "size": (640, 480),
                "format": "BGR888"
            })
            self.picam2.configure(config)
            self.picam2.start()
            print("[Camera] Picamera2 started at 640x480 (BGR888)")
            
            self.running = True
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
            print("[Camera] Thread started")
        except Exception as e:
            print(f"[Camera] ERROR: Failed to start camera: {e}")

    def _update(self):
        """Threaded loop to capture frames and run ML detection."""
        while self.running:
            try:
                # Capture frame from Picamera2 as numpy array
                frame = self.picam2.capture_array()
                if frame is None:
                    continue
                
                # Ensure we have exactly 3 channels (OpenCV DNN expects BGR)
                # Picamera2 might return 4 channels (e.g. XBGR) depending on the driver
                if frame.shape[2] == 4:
                    frame = frame[:, :, :3]
                
                # Update latest frame
                self.latest_frame = frame
                
                # Ensure ML model is loaded before processing
                if self.net is None:
                    continue

                # Run ML detection
                (h, w) = frame.shape[:2]
                
                # Prepare blob - cv2.dnn.blobFromImage handles resizing internally
                blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
                self.net.setInput(blob)
                detections = self.net.forward()

                best_detection = {"object": "none", "confidence": 0, "box": None, "frame_width": w}

                for i in range(0, detections.shape[2]):
                    confidence = detections[0, 0, i, 2]
                    if confidence > 0.5: # Confidence threshold
                        idx = int(detections[0, 0, i, 1])
                        label = self.CLASSES[idx]
                        
                        if label in self.IMPORTANT_CLASSES:
                            if confidence > best_detection["confidence"]:
                                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                                (startX, startY, endX, endY) = box.astype("int")
                                best_detection = {
                                    "object": label,
                                    "confidence": float(confidence),
                                    "box": (startX, startY, endX, endY),
                                    "frame_width": w
                                }
                
                self.current_detection = best_detection
                
            except Exception as e:
                print(f"[Camera] Capture/ML Error: {e}")
            
            # Control loop frequency to prevent CPU 100% on Zero 2 W
            # 10 FPS is usually sufficient for smart stick navigation
            time.sleep(0.05) 

    def get_latest_detection(self):
        """Returns the most recent object detection results."""
        return self.current_detection

    def get_frame(self):
        """Returns the latest captured raw frame (numpy array)."""
        return self.latest_frame

    def stop(self):
        """Safely stops camera and thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
                print("[Camera] Picamera2 stopped and closed")
            except Exception as e:
                print(f"[Camera] Error during shutdown: {e}")
