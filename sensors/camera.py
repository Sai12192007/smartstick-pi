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
    USING_MEDIAPIPE = False
except ImportError:
    try:
        import ai_edge_litert.interpreter as tflite
        TFLITE_AVAILABLE = True
        USING_MEDIAPIPE = False
    except ImportError:
        try:
            import mediapipe.tasks.python.vision as mp_vision
            TFLITE_AVAILABLE = True
            USING_MEDIAPIPE = True
            print("[Camera] Using MediaPipe Tasks API for inference.")
        except ImportError:
            TFLITE_AVAILABLE = False
            USING_MEDIAPIPE = False
            print("[Camera] WARNING: TensorFlow Lite or MediaPipe runtime not found.")

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
        self.detector = None # For MediaPipe
        self.net = None # For OpenCV DNN Fallback
        self.picam2 = None
        self.latest_frame = None
        self.current_detection = {"object": "none", "confidence": 0, "box": None}
        self.last_seen_object = "none"
        self.detection_counter = 0
        self.STABILITY_THRESHOLD = 2
        self.running = False
        self.thread = None

        # Initialize Inference Engine
        if os.path.exists(self.model_path):
            try:
                if TFLITE_AVAILABLE:
                    if USING_MEDIAPIPE:
                        base_options = mp_vision.BaseOptions(model_asset_path=self.model_path)
                        options = mp_vision.ObjectDetectorOptions(
                            base_options=base_options,
                            running_mode=mp_vision.RunningMode.IMAGE,
                            score_threshold=0.5)
                        self.detector = mp_vision.ObjectDetector.create_from_options(options)
                        print("[Camera] MediaPipe ObjectDetector loaded.")
                    else:
                        self.interpreter = tflite.Interpreter(model_path=self.model_path)
                        self.interpreter.allocate_tensors()
                        self.input_details = self.interpreter.get_input_details()
                        self.output_details = self.interpreter.get_output_details()
                        print("[Camera] TFLite Interpreter loaded.")
                else:
                    # LAST RESORT: Try loading TFLite via OpenCV DNN (Supported in OpenCV 4.10+)
                    print("[Camera] Attempting to load TFLite via OpenCV DNN...")
                    self.net = cv2.dnn.readNet(self.model_path)
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                    print("[Camera] EfficientDet loaded via OpenCV DNN successfully.")
            except Exception as e:
                print(f"[Camera] ERROR: Failed to load inference engine: {e}")
        else:
            print(f"[Camera] ERROR: Model file not found at {self.model_path}")

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
        """Threaded loop for inference."""
        while self.running:
            try:
                frame = self.picam2.capture_array()
                if frame is None:
                    continue
                
                if frame.shape[2] == 4:
                    frame = frame[:, :, :3]
                
                self.latest_frame = frame
                
                if self.interpreter is None and self.detector is None and self.net is None:
                    time.sleep(1)
                    continue

                (h, w) = frame.shape[:2]
                best_detection = {"object": "none", "confidence": 0, "box": None, "frame_width": w}

                if self.detector: # MediaPipe
                    import mediapipe as mp
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    result = self.detector.detect(mp_image)
                    if result.detections:
                        for detection in result.detections:
                            category = detection.categories[0]
                            label = category.category_name
                            confidence = category.score
                            if label in self.IMPORTANT_CLASSES and confidence > 0.5:
                                if confidence > best_detection["confidence"]:
                                    bbox = detection.bounding_box
                                    best_detection = {
                                        "object": label, "confidence": float(confidence),
                                        "box": (int(bbox.origin_x), int(bbox.origin_y), int(bbox.origin_x + bbox.width), int(bbox.origin_y + bbox.height)),
                                        "frame_width": w
                                    }
                elif self.interpreter: # TFLite Interpreter
                    input_shape = self.input_details[0]['shape']
                    input_data = cv2.resize(frame, (input_shape[2], input_shape[1]))
                    input_data = np.expand_dims(input_data, axis=0)
                    self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
                    self.interpreter.invoke()
                    boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
                    classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
                    scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]
                    count = int(self.interpreter.get_tensor(self.output_details[3]['index'])[0])

                    for i in range(count):
                        confidence = scores[i]
                        if confidence > 0.5:
                            class_id = int(classes[i])
                            label = self.CLASSES[class_id] if class_id < len(self.CLASSES) else f"unknown_{class_id}"
                            if label in self.IMPORTANT_CLASSES and confidence > best_detection["confidence"]:
                                ymin, xmin, ymax, xmax = boxes[i]
                                best_detection = {
                                    "object": label, "confidence": float(confidence),
                                    "box": (int(xmin * w), int(ymin * h), int(xmax * w), int(ymax * h)),
                                    "frame_width": w
                                }
                elif self.net: # OpenCV DNN Fallback for TFLite
                    # EfficientDet-Lite0 TFLite expects RGB [0, 255] uint8 usually
                    # blobFromImage with 1.0/1.0 scale and swapRB=True (BGR->RGB)
                    blob = cv2.dnn.blobFromImage(frame, 1.0, (320, 320), (0, 0, 0), swapRB=True, crop=False)
                    self.net.setInput(blob)
                    output = self.net.forward()
                    
                    # Normalize to [N, 7]
                    if output.ndim == 4:
                        detections = output[0, 0]
                    elif output.ndim == 3:
                        detections = output[0]
                    else:
                        detections = output

                    for i in range(detections.shape[0]):
                        confidence = detections[i, 2]
                        if confidence > 0.6: # Filter noise
                            class_id = int(detections[i, 1])
                            # Optional: print(f"[Debug] ID: {class_id} Conf: {confidence:.2f}")
                            
                            if class_id < len(self.CLASSES):
                                label = self.CLASSES[class_id]
                            else:
                                label = f"id_{class_id}"
                            
                            if label in self.IMPORTANT_CLASSES and confidence > best_detection["confidence"]:
                                box = detections[i, 3:7] * np.array([w, h, w, h])
                                best_detection = {
                                    "object": label, "confidence": float(confidence),
                                    "box": box.astype("int"), "frame_width": w
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
