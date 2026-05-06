import cv2
import numpy as np
import threading
import os
import time

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
        self.cap = None
        self.current_detection = {"object": "none", "confidence": 0, "box": None}
        self.running = False
        self.thread = None

        if os.path.exists(self.model_path) and os.path.exists(self.prototxt_path):
            self.net = cv2.dnn.readNetFromCaffe(self.prototxt_path, self.model_path)
            print("[Camera] ML Model loaded successfully")
        else:
            print("[Camera] ERROR: Model files not found. Run setup.py first.")

    def start(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[Camera] ERROR: Could not open video source")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        print("[Camera] Thread started")

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Optimization: Resize frame for faster processing
            frame = cv2.resize(frame, (300, 300))
            (h, w) = frame.shape[:2]
            
            # Prepare blob
            blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
            self.net.setInput(blob)
            detections = self.net.forward()

            best_detection = {"object": "none", "confidence": 0, "box": None}

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
            time.sleep(0.1) # Limit FPS to save CPU

    def get_latest_detection(self):
        return self.current_detection

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
