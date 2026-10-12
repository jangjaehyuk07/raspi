import unittest
from unittest.mock import patch, Mock
from gpiozero import LED, OutputDevice
from gpiozero.pins.mock import MockFactory
import distance_led as app


class Tests(unittest.TestCase):
    def setUp(self):
        self.factory = MockFactory()
        self.addCleanup(self.factory.close)
        # 테스트용 가상 핀이며 실제 배선 번호가 아닙니다.
        self.red = LED(5, pin_factory=self.factory)
        self.green = LED(6, pin_factory=self.factory)
        self.trigger = OutputDevice(7, pin_factory=self.factory)
        self.yellow = LED(8, pin_factory=self.factory)
        for device in (self.red, self.green, self.trigger, self.yellow):
            self.addCleanup(device.close)

    def test_threshold_and_invalid(self):
        for distance, expected in [(2, (1, 0)), (15, (1, 0)), (15.01, (0, 1)),
                                   (400, (0, 1)), (None, (0, 0)),
                                   (float('nan'), (0, 0)), (401, (0, 0)), (0, (0, 0))]:
            app.set_leds(distance, self.red, self.green)
            self.assertEqual((self.red.value, self.green.value), expected)

    def test_never_both_on(self):
        for device in (self.red, self.green):
            original = device.on
            def checked(original=original):
                original()
                self.assertFalse(self.red.value and self.green.value)
            device.on = checked
        for distance in (20, 10, 20, 15):
            app.set_leds(distance, self.red, self.green)

    def test_measurement(self):
        class Echo:
            values = iter([0, 0, 1, 1, 0])
            @property
            def value(self):
                return next(self.values)
        with patch.object(app.time, 'sleep'), patch.object(app.time, 'monotonic', side_effect=[0, 0, 0, 0.0001, 0.001]):
            self.assertAlmostEqual(app.measure_distance(self.trigger, Echo()), 17.15)
        self.assertFalse(self.trigger.value)

    def test_no_echo_timeout(self):
        class Echo:
            value = 0
        with patch.object(app.time, 'sleep'), patch.object(app.time, 'monotonic', side_effect=[0, 0.04]):
            with self.assertRaises(TimeoutError):
                app.measure_distance(self.trigger, Echo())

    def test_stuck_high(self):
        class Echo:
            value = 1
        with self.assertRaises(ValueError):
            app.measure_distance(self.trigger, Echo())

    def test_no_falling_edge(self):
        class Echo:
            values = iter([0, 1, 1])
            @property
            def value(self):
                return next(self.values)
        with patch.object(app.time, 'sleep'), patch.object(app.time, 'monotonic', side_effect=[0, 0, 0.04]):
            with self.assertRaises(TimeoutError):
                app.measure_distance(self.trigger, Echo())

    def test_error_logging_and_leds_off(self):
        with patch.object(app, 'measure_distance', side_effect=TimeoutError('no echo')), \
             patch.object(app.time, 'sleep', side_effect=KeyboardInterrupt), \
             self.assertLogs(level='WARNING') as logs:
            with self.assertRaises(KeyboardInterrupt):
                app.run(self.trigger, None, self.red, self.green)
        self.assertIn('no echo', logs.output[0])
        self.assertEqual((self.red.value, self.green.value), (0, 0))

    def test_shutdown(self):
        self.red.on()
        self.yellow.on()
        with patch.object(app, 'measure_distance', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                app.run(self.trigger, None, self.red, self.green, Mock(), self.yellow)
        self.assertEqual((self.red.value, self.green.value, self.trigger.value), (0, 0, 0))
        self.assertFalse(self.yellow.value)

    def test_climate_thresholds(self):
        for temperature, humidity, expected in [(27, 69, 0), (28, 50, 1),
                                                (20, 70, 1), (30, 80, 1),
                                                (None, 50, 0), (20, 101, 0),
                                                (float('nan'), 50, 0)]:
            with self.subTest(temperature=temperature, humidity=humidity):
                app.update_climate(Mock(temperature=temperature, humidity=humidity), self.yellow)
                self.assertEqual(self.yellow.value, expected)

    def test_climate_read_error(self):
        class Sensor:
            @property
            def temperature(self):
                raise RuntimeError('checksum error')
        self.yellow.on()
        with self.assertLogs(level='WARNING') as logs:
            app.update_climate(Sensor(), self.yellow)
        self.assertFalse(self.yellow.value)
        self.assertIn('checksum error', logs.output[0])


if __name__ == '__main__':
    unittest.main()
