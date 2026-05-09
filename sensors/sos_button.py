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
        """Monitor the latching switch for OFF -> ON transitions (HIGH -> LOW)."""
        # Initial state setup
        if HAS_GPIO:
            last_state = GPIO.input(self.pin)
        else:
            last_state = 1 # HIGH (OFF)
            
        while self.running:
            if HAS_GPIO:
                current_state = GPIO.input(self.pin)
                
                # Detect OFF -> ON transition (Falling Edge: HIGH -> LOW)
                # Since we use pull-up, LOW means the switch is closed (ON)
                if last_state == 1 and current_state == 0:
                    print("\n[SOS] Emergency latch triggered (ON)")
                    if self.callback:
                        self.callback()
                
                last_state = current_state
            
            # Polling at 20Hz (50ms) provides low CPU usage and 
            # natural debounce for mechanical switches.
            time.sleep(0.05)

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
