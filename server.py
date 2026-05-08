import socket
import threading
import json
import time
from flask import Flask, Response
from flask_cors import CORS

class DualServer:
    def __init__(self, camera_system, ultrasonic_sensor):
        self.camera = camera_system
        self.ultrasonic = ultrasonic_sensor
        
        # Sensor Server (Port 5000)
        self.sensor_host = "0.0.0.0"
        self.sensor_port = 5000
        self.sensor_socket = None
        
        # MJPEG Server (Port 5001)
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_mjpeg_routes()
        
        self.running = False

    def _setup_mjpeg_routes(self):
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self.camera.generate_mjpeg(),
                            mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/')
        def index():
            return "Smart Stick MJPEG Stream Server is Running on /video_feed"

    def start(self):
        self.running = True
        
        # Start Sensor Server Thread
        sensor_thread = threading.Thread(target=self._run_sensor_server, daemon=True)
        sensor_thread.start()
        
        # Start MJPEG Server Thread
        mjpeg_thread = threading.Thread(target=self._run_mjpeg_server, daemon=True)
        mjpeg_thread.start()
        
        print(f"[Server] Sensor Server: port {self.sensor_port}")
        print(f"[Server] MJPEG Stream: http://0.0.0.0:5001/video_feed")

    def _run_mjpeg_server(self):
        # Run Flask on port 5001
        self.app.run(host='0.0.0.0', port=5001, threaded=True, use_reloader=False)

    def _run_sensor_server(self):
        self.sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sensor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.sensor_socket.bind((self.sensor_host, self.sensor_port))
            self.sensor_socket.listen(5)
            
            while self.running:
                client_sock, addr = self.sensor_socket.accept()
                print(f"[Server] Client connected to Sensor API: {addr}")
                
                client_thread = threading.Thread(
                    target=self._handle_sensor_client, 
                    args=(client_sock,), 
                    daemon=True
                )
                client_thread.start()
        except Exception as e:
            print(f"[Server] Sensor socket error: {e}")

    def _handle_sensor_client(self, client_sock):
        try:
            while self.running:
                distance = self.ultrasonic.get_distance()
                
                # Format JSON payload
                payload = {
                    "distance": round(distance, 1),
                    "alert": distance < 30, # Critical obstacle alert
                    "timestamp": time.time()
                }
                
                message = json.dumps(payload) + "\n"
                client_sock.sendall(message.encode('utf-8'))
                
                time.sleep(0.1) # 10Hz updates for sensors
        except (ConnectionResetError, BrokenPipeError):
            print("[Server] Sensor client disconnected")
        finally:
            client_sock.close()

    def stop(self):
        self.running = False
        if self.sensor_socket:
            self.sensor_socket.close()
        print("[Server] Stopped")
