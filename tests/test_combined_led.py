import importlib.util
from pathlib import Path
import unittest
from gpiozero import LED
from gpiozero.pins.mock import MockFactory

path = Path(__file__).resolve().parents[1] / '2026591025/source/combined_led.py'
spec = importlib.util.spec_from_file_location('combined_led', path)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class CombinedTests(unittest.TestCase):
    def setUp(self):
        self.factory = MockFactory()
        self.addCleanup(self.factory.close)
        self.red = LED(17, pin_factory=self.factory)
        self.green = LED(27, pin_factory=self.factory)
        self.yellow = LED(22, pin_factory=self.factory)
        for led in (self.red, self.green, self.yellow):
            self.addCleanup(led.close)

    def test_distance(self):
        for distance, expected in [(15, (1, 0)), (15.01, (0, 1)), (2, (1, 0))]:
            app.set_distance_leds(distance, self.red, self.green)
            self.assertEqual((self.red.value, self.green.value), expected)

    def test_climate_including_dht22_range(self):
        for t, h, expected in [(27, 69, 0), (28, 69, 1), (27, 70, 1),
                               (-10, 50, 0), (60, 50, 1)]:
            app.set_climate_led(t, h, self.yellow)
            self.assertEqual(self.yellow.value, expected)

    def test_invalid_values_turn_off_leds(self):
        self.red.on()
        with self.assertRaises(ValueError):
            app.set_distance_leds(float('nan'), self.red, self.green)
        self.assertFalse(self.red.value or self.green.value)
        self.yellow.on()
        with self.assertRaises(ValueError):
            app.set_climate_led(None, 50, self.yellow)
        self.assertFalse(self.yellow.value)
