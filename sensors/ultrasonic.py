import time
import random

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

class UltrasonicSensor:
    def __init__(self, trig_pin=23, echo_pin=24):
        self.trig = trig_pin
        self.echo = echo_pin
        
        if HAS_GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.trig, GPIO.OUT)
            GPIO.setup(self.echo, GPIO.IN)
            print(f"[Ultrasonic] Real mode initialized (Trig: {self.trig}, Echo: {self.echo})")
        else:
            print("[Ultrasonic] Simulation mode active")

    def get_distance(self):
        if not HAS_GPIO:
            return random.randint(10, 150)
        
        # Real sensor logic
        GPIO.output(self.trig, False)
        time.sleep(0.000002) # wait for sensor to settle
        
        GPIO.output(self.trig, True)
        time.sleep(0.00001)
        GPIO.output(self.trig, False)
        
        start_time = time.time()
        stop_time = time.time()
        
        # Wait for Echo to go high
        timeout = time.time() + 0.1
        while GPIO.input(self.echo) == 0:
            start_time = time.time()
            if start_time > timeout:
                return 150 # Timeout, assume clear path
                
        # Wait for Echo to go low
        timeout = time.time() + 0.1
        while GPIO.input(self.echo) == 1:
            stop_time = time.time()
            if stop_time > timeout:
                break
                
        duration = stop_time - start_time
        distance = (duration * 34300) / 2 # Speed of sound 34300 cm/s
        
        return round(distance, 2)

    def cleanup(self):
        if HAS_GPIO:
            GPIO.cleanup([self.trig, self.echo])
