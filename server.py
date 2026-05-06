import socket
import threading
import time

class SocketServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        print(f"[Server] Listening on {self.host}:{self.port}")

    def _listen(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)

        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                try:
                    self.client_socket, addr = self.server_socket.accept()
                    print(f"[Server] Client connected from {addr}")
                except socket.timeout:
                    continue
                
                # While client is connected, keep the connection open
                while self.running:
                    try:
                        # Check if connection is still alive
                        # This is a bit tricky in Python, but we'll try to send an empty byte
                        self.client_socket.send(b"", socket.MSG_PEEK)
                        time.sleep(1)
                    except (socket.error, BrokenPipeError):
                        print("[Server] Client disconnected")
                        self.client_socket.close()
                        self.client_socket = None
                        break
            except Exception as e:
                print(f"[Server] Error: {e}")
                time.sleep(1)

    def send_data(self, data):
        if self.client_socket:
            try:
                self.client_socket.sendall(data.encode('utf-8'))
                return True
            except Exception as e:
                print(f"[Server] Failed to send data: {e}")
                self.client_socket = None
        return False

    def stop(self):
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
