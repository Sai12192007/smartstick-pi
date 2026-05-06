import time
import threading

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

class Buzzer:
    def __init__(self, pin=18):
        self.pin = pin
        self.beeping = False
        self.beep_interval = 0  # 0 means no beep
        self.thread = None
        self.stop_event = threading.Event()
        
        if HAS_GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            print(f"[Buzzer] Real mode initialized on GPIO {self.pin}")
        else:
            print("[Buzzer] Simulation mode active")

    def _beep_loop(self):
        while not self.stop_event.is_set():
            if self.beep_interval > 0:
                if HAS_GPIO:
                    GPIO.output(self.pin, GPIO.HIGH)
                    time.sleep(0.1)
                    GPIO.output(self.pin, GPIO.LOW)
                    time.sleep(self.beep_interval)
                else:
                    print(f"[Buzzer Simulation] BEEP! (Interval: {self.beep_interval}s)")
                    time.sleep(self.beep_interval + 0.1)
            else:
                time.sleep(0.1)

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._beep_loop, daemon=True)
        self.thread.start()

    def set_distance(self, distance):
        """
        Logic:
        < 30 cm -> fast beep (0.1s interval)
        30 - 100 cm -> slow beep (0.5s interval)
        > 100 cm -> no beep (interval 0)
        """
        if distance < 30:
            self.beep_interval = 0.1
        elif distance < 100:
            self.beep_interval = 0.5
        else:
            self.beep_interval = 0

    def cleanup(self):
        self.stop_event.set()
        if HAS_GPIO:
            GPIO.cleanup(self.pin)
