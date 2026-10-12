# Raspberry Pi 센서·LED 실습

HC-SR04와 DHT22로 거리·온습도를 측정하고 LED를 제어합니다.

| 조건 | 표시 |
|---|---|
| 거리 ≤ 15cm | 빨강 ON, 초록 OFF |
| 거리 > 15cm | 초록 ON, 빨강 OFF |
| 온도 ≥ 28°C 또는 습도 ≥ 70% | 노랑 ON |
| 온도 < 28°C 그리고 습도 < 70% | 노랑 OFF |

측정 오류 시 해당 LED를 끕니다. 노란 LED는 냉방·제습 권장 표시이며 실제 가전제품을 제어하지 않습니다.

## 파일

- `2026591025/source/combined_led.py`: 최종 통합 코드. gpiozero DistanceSensor와 DHT22 사용.
- `2026591025/source/ultrasonic_led.py`: 초음파·빨강·초록만 테스트. 직접 펄스 측정, 30ms 타임아웃.
- `2026591025/source/sensor_led.py`: IDLE용 직접 펄스 측정 통합 버전.
- `distance_led.py`: 직접 펄스 측정 통합 버전의 CLI 실행 파일. 핀 번호 변경 가능.
- `tests/`: 가상 GPIO 자동 테스트. 실제 센서 검증을 대체하지 않습니다.

## 배선 (BCM 번호)

전원을 끄고 전원 케이블을 분리한 뒤 작업합니다.

| 장치 단자 | 연결 | 물리 핀 |
|---|---|---|
| HC-SR04 VCC | 5V | 2 |
| HC-SR04 TRIG | GPIO23 | 16 |
| HC-SR04 ECHO | 분압 후 GPIO24 | 18 |
| 센서·LED GND | 공통 GND | 6 또는 다른 GND 핀 |
| DHT22 VCC | 3.3V | 1 |
| DHT22 DATA | GPIO4 | 7 |
| 빨간 LED | GPIO17 → 330Ω → A(+) | 11 |
| 초록 LED | GPIO27 → 330Ω → A(+) | 13 |
| 노란 LED | GPIO22 → 330Ω → A(+) | 15 |

각 LED K(-)는 GND에 연결합니다. 브레드보드의 `-` 레일은 실제 GND와 연결해야 합니다. 레일 중간 단절과 양쪽 레일의 독립 연결 여부를 확인하세요.

HC-SR04 ECHO의 5V를 GPIO에 직접 연결하면 안 됩니다.

```text
ECHO ── 2.2kΩ ──┬── GPIO24
                │
              3.3kΩ
                │
               GND
```

접점 전압은 명목상 약 3.0V입니다. 저항 오차와 전원을 고려해 GPIO 입력이 3.3V 이하인지 확인하세요.
DHT22 단자 순서는 실제 제품 표시를 따릅니다. NC는 연결하지 않습니다. 풀업이 없는 센서는 DATA와 3.3V 사이에 10kΩ 저항을 추가합니다.

## Raspberry Pi OS 설치·실행

```sh
sudo apt update
sudo apt install python3-venv python3-gpiozero python3-lgpio idle
cd ~/2026591025/source
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install adafruit-circuitpython-dht==4.0.12
.venv/bin/python -m idlelib combined_led.py
```

저장 위치가 다르면 실제 경로로 이동하세요. IDLE에서 F5로 실행하고 회로 안전성을 직접 확인한 경우에만 `확인`을 입력합니다. Ctrl+C로 종료하면 LED를 끄고 자원을 정리합니다.
거리 출력은 약 0.5초 간격, DHT22는 2초 이상 간격입니다. DHT 읽기 중 거리 출력이 지연될 수 있습니다.

`max_distance=2`의 단위는 m이며, 15cm 판정 기준과 별개입니다. `PWMSoftwareFallback`은 정밀도 경고입니다.
DHT22를 DHT11로 초기화하면 잘못된 값이 나올 수 있습니다.
DistanceSensor는 백그라운드 측정값을 사용하므로 센서 오류 시 이전 값이 잠시 남을 수 있습니다. 응답 타임아웃을 직접 확인하려면 초음파 전용 테스트 파일을 사용하세요.

## 클라우드 자동 테스트

```sh
cd /workspace/raspi
python3 -m venv /workspace/raspi-venv
/workspace/raspi-venv/bin/python -m pip install -r requirements-dev.txt
/workspace/raspi-venv/bin/python -m unittest discover -s tests -v
```

클라우드는 x86_64이며 실제 GPIO가 없습니다. 사용자는 LED·초음파 동작 성공을 보고했지만, 클라우드에서 실제 배선 안전성 및 DHT22 통합 실측은 확인하지 못했습니다.
