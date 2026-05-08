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

try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    try:
        import ai_edge_litert.interpreter as tflite
        TFLITE_AVAILABLE = True
    except ImportError:
        TFLITE_AVAILABLE = False
        print("[Camera] WARNING: TensorFlow Lite runtime not found.")

class CameraSystem:
    def __init__(self, model_path="models/efficientdet_lite0.tflite", label_path="models/labels.txt"):
        self.model_path = model_path
        self.label_path = label_path
        
        # Load labels
        self.CLASSES = []
        if os.path.exists(self.label_path):
            with open(self.label_path, 'r') as f:
                self.CLASSES = [line.strip() for line in f.readlines()]
        else:
            # Fallback COCO-like labels if file missing
            self.CLASSES = ["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat"]
        
        # Filter for important objects
        self.IMPORTANT_CLASSES = ["person", "car", "chair", "bottle", "bus", "dog", "cat", "bicycle", "motorcycle"]
        
        self.interpreter = None
        self.picam2 = None
        self.latest_frame = None
        self.current_detection = {"object": "none", "confidence": 0, "box": None}
        self.last_seen_object = "none"
        self.detection_counter = 0
        self.STABILITY_THRESHOLD = 2
        self.running = False
        self.thread = None

        # Initialize TFLite Interpreter
        if TFLITE_AVAILABLE and os.path.exists(self.model_path):
            try:
                self.interpreter = tflite.Interpreter(model_path=self.model_path)
                self.interpreter.allocate_tensors()
                self.input_details = self.interpreter.get_input_details()
                self.output_details = self.interpreter.get_output_details()
                print(f"[Camera] TFLite EfficientDet loaded successfully. Input: {self.input_details[0]['shape']}")
            except Exception as e:
                print(f"[Camera] ERROR: Failed to load TFLite model: {e}")
        else:
            print("[Camera] ERROR: TFLite model or runtime missing.")

        # Initialize Picamera2 instance
        if PICAMERA2_AVAILABLE:
            try:
                self.picam2 = Picamera2()
                print("[Camera] Picamera2 initialized")
            except Exception as e:
                print(f"[Camera] ERROR: Could not initialize Picamera2: {e}")

    def start(self):
        if not self.picam2:
            print("[Camera] ERROR: Camera not initialized")
            return
        
        try:
            config = self.picam2.create_video_configuration(main={"size": (640, 480), "format": "BGR888"})
            self.picam2.configure(config)
            self.picam2.start()
            print("[Camera] Picamera2 started at 640x480 (BGR888)")
            
            self.running = True
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
            print("[Camera] Detection thread started")
        except Exception as e:
            print(f"[Camera] ERROR: Failed to start camera: {e}")

    def _update(self):
        """Threaded loop for TFLite inference."""
        while self.running:
            try:
                frame = self.picam2.capture_array()
                if frame is None:
                    continue
                
                # Ensure 3 channels
                if frame.shape[2] == 4:
                    frame = frame[:, :, :3]
                
                self.latest_frame = frame
                
                if self.interpreter is None:
                    time.sleep(1)
                    continue

                # Pre-processing for EfficientDet-Lite0 (320x320)
                input_shape = self.input_details[0]['shape']
                input_data = cv2.resize(frame, (input_shape[2], input_shape[1]))
                input_data = np.expand_dims(input_data, axis=0)

                # Set tensor
                self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
                
                # Run Inference
                self.interpreter.invoke()

                # Get results (Standard TFLite Object Detection Output)
                # [1, 10, 4] Boxes, [1, 10] Classes, [1, 10] Scores, [1] count
                boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
                classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
                scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]
                count = int(self.interpreter.get_tensor(self.output_details[3]['index'])[0])

                (h, w) = frame.shape[:2]
                best_detection = {"object": "none", "confidence": 0, "box": None, "frame_width": w}

                for i in range(count):
                    confidence = scores[i]
                    if confidence > 0.5: # EfficientDet is more accurate, can use 0.5
                        class_id = int(classes[i])
                        if class_id < len(self.CLASSES):
                            label = self.CLASSES[class_id]
                        else:
                            label = f"unknown_{class_id}"
                        
                        if label in self.IMPORTANT_CLASSES:
                            if confidence > best_detection["confidence"]:
                                # Box format: [ymin, xmin, ymax, xmax] (normalized)
                                ymin, xmin, ymax, xmax = boxes[i]
                                (startX, startY, endX, endY) = (int(xmin * w), int(ymin * h), int(xmax * w), int(ymax * h))
                                
                                best_detection = {
                                    "object": label,
                                    "confidence": float(confidence),
                                    "box": (startX, startY, endX, endY),
                                    "frame_width": w
                                }
                
                # Stability Filter
                if best_detection["object"] == self.last_seen_object and best_detection["object"] != "none":
                    self.detection_counter += 1
                else:
                    self.last_seen_object = best_detection["object"]
                    self.detection_counter = 0

                if self.detection_counter >= self.STABILITY_THRESHOLD or best_detection["object"] == "none":
                    self.current_detection = best_detection
                
            except Exception as e:
                print(f"[Camera] TFLite Error: {e}")
            
            time.sleep(0.01) # Faster loop for TFLite

    def get_latest_detection(self):
        return self.current_detection

    def get_frame(self):
        return self.latest_frame

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
