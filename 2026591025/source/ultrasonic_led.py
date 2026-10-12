"""HC-SR04 거리 측정과 LED 제어. 핀 번호는 BCM 기준입니다."""
import argparse
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


def run(trigger, echo, red, green):
    try:
        while True:
            try:
                distance = measure_distance(trigger, echo)
                set_leds(distance, red, green)
                logging.info("거리: %.1fcm", distance)
            except (TimeoutError, ValueError) as error:
                set_leds(None, red, green)
                logging.warning("측정 실패: %s", error)
            time.sleep(0.1)  # 다음 측정까지 충분한 간격을 둡니다.
    finally:
        red.off()
        green.off()
        trigger.off()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    # 사용자가 제공한 코드에서 확인된 BCM 번호입니다.
    for name, pin in {'trig': 23, 'echo': 24, 'red': 17, 'green': 27}.items():
        parser.add_argument('--' + name, type=int, default=pin)
    parser.add_argument('--echo-safe', action='store_true',
                        help='ECHO가 분압/레벨 변환을 통해 3.3V 이하임을 직접 확인한 경우만 지정')
    args = parser.parse_args(argv)
    pins = [args.trig, args.echo, args.red, args.green]
    if len(set(pins)) != 4 or any(pin < 0 or pin > 27 for pin in pins):
        parser.error('서로 다른 BCM GPIO 번호(0~27)를 지정하세요. 보드에서 사용 가능한 핀인지 확인하세요.')
    if not args.echo_safe:
        print('실행 전: ECHO 분압/레벨 변환, LED 저항과 배선을 확인하세요.')
        answer = input('회로 안전성을 직접 확인했다면 확인을 입력하세요 (미확인 시 Enter): ')
        if answer.strip() != '확인':
            print('안전 미확인: GPIO를 실행하지 않습니다.')
            return
    model = Path('/proc/device-tree/model')
    if not model.exists() or 'Raspberry Pi' not in model.read_text():
        parser.error('실제 Raspberry Pi에서만 하드웨어 모드를 실행할 수 있습니다.')
    from gpiozero import DigitalInputDevice, OutputDevice, LED
    from gpiozero.pins.lgpio import LGPIOFactory
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        # 일부 장치 생성이 실패해도 이미 열린 GPIO를 정리합니다.
        with ExitStack() as stack:
            factory = LGPIOFactory()
            stack.callback(factory.close)
            trigger = stack.enter_context(OutputDevice(args.trig, initial_value=False, pin_factory=factory))
            echo = stack.enter_context(DigitalInputDevice(args.echo, pull_up=False, pin_factory=factory))
            red = stack.enter_context(LED(args.red, initial_value=False, pin_factory=factory))
            green = stack.enter_context(LED(args.green, initial_value=False, pin_factory=factory))
            run(trigger, echo, red, green)
    except KeyboardInterrupt:
        logging.info('종료: LED를 끄고 GPIO를 정리했습니다.')


if __name__ == '__main__':
    main([])  # IDLE의 Run Module(F5)로 실행합니다.
