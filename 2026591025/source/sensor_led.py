"""HC-SR04 거리 측정과 LED 제어. 핀 번호는 BCM 기준입니다."""
from contextlib import ExitStack
import logging
import math
from pathlib import Path
import time


def set_leds(distance, red, green):
    # 먼저 둘 다 꺼서 두 LED가 동시에 켜지지 않도록 합니다.
    red.off()
    green.off()
    if distance is None or not math.isfinite(distance) or not 2 <= distance <= 400:
        return
    (red if distance <= 15 else green).on()


def measure_distance(trigger, echo, timeout=0.03):
    if echo.value:
        raise ValueError("측정 전 ECHO가 HIGH입니다. 배선과 센서를 확인하세요.")
    trigger.on()
    try:
        time.sleep(0.00001)  # 센서에 10μs 펄스를 보냅니다.
    finally:
        trigger.off()
    deadline = time.monotonic() + timeout
    while not echo.value:
        if time.monotonic() >= deadline:
            raise TimeoutError("ECHO 상승 신호가 없습니다.")
    start = time.monotonic()
    deadline = start + timeout
    while echo.value:
        if time.monotonic() >= deadline:
            raise TimeoutError("ECHO 하강 신호가 없습니다.")
    distance = (time.monotonic() - start) * 34300 / 2
    if not 2 <= distance <= 400:
        raise ValueError(f"센서 측정 범위를 벗어났습니다: {distance:.1f}cm")
    return distance


def update_climate(sensor, yellow):
    try:
        temperature = sensor.temperature
        humidity = sensor.humidity
        if (temperature is None or humidity is None
                or not math.isfinite(temperature) or not math.isfinite(humidity)
                or not -40 <= temperature <= 80 or not 0 <= humidity <= 100):
            raise ValueError('온습도 값이 없거나 비정상입니다.')
        # 덥거나 습하면 냉방/제습 사용을 권장합니다.
        recommended = temperature >= 28 or humidity >= 70
        yellow.on() if recommended else yellow.off()
        logging.info('온도: %.1f°C, 습도: %.1f%%, %s', temperature, humidity,
                     '냉방/제습 사용 권장' if recommended else '설정 기준 미만')
    except (RuntimeError, ValueError) as error:
        yellow.off()  # 측정 실패 시 이전 표시를 유지하지 않습니다.
        logging.warning('온습도 측정 실패: %s', error)


def run(trigger, echo, red, green, sensor=None, yellow=None):
    next_climate = 0
    try:
        while True:
            try:
                distance = measure_distance(trigger, echo)
                set_leds(distance, red, green)
                logging.info("거리: %.1fcm", distance)
            except (TimeoutError, ValueError) as error:
                set_leds(None, red, green)
                logging.warning("측정 실패: %s", error)
            if sensor is not None and time.monotonic() >= next_climate:
                update_climate(sensor, yellow)
                next_climate = time.monotonic() + 2  # DHT22은 2초 이상 간격으로 읽습니다.
            time.sleep(0.1)  # 다음 측정까지 충분한 간격을 둡니다.
    finally:
        red.off()
        green.off()
        trigger.off()
        if yellow is not None:
            yellow.off()


def main():
    answer = input('ECHO 분압, DHT 데이터 3.3V 이하, LED 저항 확인 후 확인 입력: ')
    if answer.strip() != '확인':
        print('안전 미확인: 실행하지 않습니다.')
        return
    model = Path('/proc/device-tree/model')
    if not model.exists() or 'Raspberry Pi' not in model.read_text():
        print('실제 Raspberry Pi에서 실행하세요.')
        return
    from gpiozero import DigitalInputDevice, OutputDevice, LED
    from gpiozero.pins.lgpio import LGPIOFactory
    import board
    import adafruit_dht
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        # 일부 장치 생성이 실패해도 이미 열린 GPIO를 정리합니다.
        with ExitStack() as stack:
            factory = LGPIOFactory()
            stack.callback(factory.close)
            trigger = stack.enter_context(OutputDevice(23, initial_value=False, pin_factory=factory))
            echo = stack.enter_context(DigitalInputDevice(24, pull_up=False, pin_factory=factory))
            red = stack.enter_context(LED(17, initial_value=False, pin_factory=factory))
            green = stack.enter_context(LED(27, initial_value=False, pin_factory=factory))
            yellow = stack.enter_context(LED(22, initial_value=False, pin_factory=factory))
            sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
            stack.callback(sensor.exit)
            run(trigger, echo, red, green, sensor, yellow)
    except KeyboardInterrupt:
        logging.info('종료: LED를 끄고 GPIO를 정리했습니다.')


if __name__ == '__main__':
    main()  # IDLE의 Run Module(F5)로 실행합니다.
