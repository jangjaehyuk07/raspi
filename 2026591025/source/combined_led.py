import time
import math
from contextlib import ExitStack


def set_distance_leds(distance, red, green):
    red.off()
    green.off()
    if not math.isfinite(distance) or not 2 <= distance <= 200:
        raise ValueError('거리 값이 없거나 측정 범위 밖입니다.')
    if distance <= 15:
        red.on()
        return '위험 / 빨강 ON'
    green.on()
    return '안전 / 초록 ON'


def set_climate_led(temperature, humidity, yellow):
    yellow.off()
    if (temperature is None or humidity is None
            or not math.isfinite(temperature) or not math.isfinite(humidity)
            or not -40 <= temperature <= 80 or not 0 <= humidity <= 100):
        raise ValueError('온습도 값이 없거나 비정상입니다.')
    if temperature >= 28 or humidity >= 70:
        yellow.on()
        return '냉방/제습 사용 권장'
    return '설정 기준 미만 / 노랑 OFF'


def main():
    answer = input('ECHO 분압, DHT 데이터 3.3V 이하, LED 저항 확인 후 확인 입력: ')
    if answer.strip() != '확인':
        print('안전 미확인: 실행하지 않습니다.')
        return

    import board
    import adafruit_dht
    from gpiozero import LED, DistanceSensor

    with ExitStack() as stack:
        # GPIO 번호는 BCM 기준입니다.
        red = stack.enter_context(LED(17, initial_value=False))
        green = stack.enter_context(LED(27, initial_value=False))
        yellow = stack.enter_context(LED(22, initial_value=False))
        distance_sensor = stack.enter_context(DistanceSensor(
            echo=24, trigger=23, max_distance=2,
            queue_len=1, partial=True
        ))
        dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        stack.callback(dht_sensor.exit)

        next_climate = 0
        try:
            while True:
                try:
                    distance = distance_sensor.distance * 100
                    state = set_distance_leds(distance, red, green)
                    print(f'거리: {distance:.1f}cm / {state}')
                except (RuntimeError, ValueError) as error:
                    red.off()
                    green.off()
                    print(f'거리 측정 오류: {error}')

                # 거리 확인은 0.5초 간격, DHT22은 2초 이상 간격입니다.
                if time.monotonic() >= next_climate:
                    try:
                        temperature = dht_sensor.temperature
                        humidity = dht_sensor.humidity
                        state = set_climate_led(temperature, humidity, yellow)
                        print(f'온도: {temperature:.1f}°C / 습도: {humidity:.1f}%')
                        print(f'온습도 상태: {state}')
                    except (RuntimeError, ValueError) as error:
                        yellow.off()
                        print(f'온습도 측정 오류: {error}')
                    next_climate = time.monotonic() + 2

                time.sleep(0.5)

        except KeyboardInterrupt:
            print('프로그램을 종료합니다.')
        finally:
            red.off()
            green.off()
            yellow.off()
    # with 블록 종료 시 센서와 GPIO를 자동으로 정리합니다.


if __name__ == '__main__':
    main()
