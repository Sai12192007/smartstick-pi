import time
import threading

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

class SOSButton:
    def __init__(self, pin=17, callback=None):
        """
        Initialize the SOS Button.
        :param pin: GPIO pin number (BCM)
        :param callback: Function to call when SOS is triggered
        """
        self.pin = pin
        self.callback = callback
        self.running = False
        self.thread = None
        
        if HAS_GPIO:
            GPIO.setmode(GPIO.BCM)
            # Configure with internal pull-up resistor
            # Button connected between pin and GND
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            print(f"[SOS Button] Real mode initialized on GPIO {self.pin}")
        else:
            print("[SOS Button] Simulation mode active")

    def start(self):
        """Start the button monitoring thread."""
        self.running = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()

    def _monitor(self):
        """Monitor the button for a 3-second long press."""
        while self.running:
            if HAS_GPIO:
                # Button pressed when pin is LOW (GND)
                if GPIO.input(self.pin) == GPIO.LOW:
                    press_start = time.time()
                    triggered = False
                    
                    while GPIO.input(self.pin) == GPIO.LOW:
                        elapsed = time.time() - press_start
                        if elapsed >= 3.0 and not triggered:
                            print("\n[SOS] Emergency button triggered")
                            if self.callback:
                                self.callback()
                            triggered = True
                        time.sleep(0.1) # Debounce/Poll interval
                        
                    # Reset triggered state when button is released
                    triggered = False
            
            time.sleep(0.1) # Polling interval for low CPU usage

    def stop(self):
        """Stop the monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def cleanup(self):
        """Cleanup GPIO settings."""
        self.stop()
        if HAS_GPIO:
            # Only cleanup our specific pin to avoid breaking other sensors
            try:
                GPIO.cleanup(self.pin)
            except Exception:
                pass
