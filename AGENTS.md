# MODU-C ZMK Config — Agent Guidelines, Architecture & Analysis

이 문서는 Antigravity 및 AI 에이전트가 이 프로젝트(`modu-c-zmk-config`)를 작업할 때 참고해야 하는 **하드웨어/펌웨어 심층 분석**, **키맵 및 레이어 아키텍처**, **빌드/검증 파이프라인**, 그리고 **사용자 필수 준수 규칙**을 집대성한 가이드입니다.

---

## 1. 프로젝트 개요 및 핵심 파일 구성

- **키보드 모델**: MODU-C (무선 인체공학 스플릿 키보드)
- **베이스 펌웨어**: ZMK Firmware (Zephyr RTOS 기반)
- **업스트림 소스 커밋**: `22sh22/modu-c-firmware` (`bee0bb4b812f63f279eb67e928accc89600b5904`)
- **핵심 파일 위치**:
  - 키맵 소스: [`config/modu.keymap`](config/modu.keymap)
  - 레이아웃 메타데이터: [`config/modu.json`](config/modu.json), [`config/info.json`](config/info.json) (두 파일은 항상 동일한 내용을 유지해야 함)
  - 빌드 매트릭스 및 모듈: [`build.yaml`](build.yaml), [`config/west.yml`](config/west.yml)
  - CI/CD 자동 빌드 워크플로우: [`.github/workflows/build.yml`](.github/workflows/build.yml)
  - 사용자 가이드 문서: [`KEYMAP_GUIDE.md`](KEYMAP_GUIDE.md)

---

## 2. 하드웨어 및 펌웨어 아키텍처 분석

### ① MCU 및 부트로더
- **MCU 모듈**: Minewsemi MS88SF3 (Nordic Semiconductor nRF52840, ARM Cortex-M4F)
- **빌드 타깃 보드**: `ms88sf3/nrf52840`
- **부트로더**: Adafruit nRF52 UF2 Bootloader
- **UF2 패밀리 ID**: `0xADA52840` (nRF52840 전용 매직 ID)

### ② 무선 스플릿 (Split) 역할 분담
- **Central (좌측, `modu_left`)**:
  - BLE 및 USB 호스트 연결 주관
  - 좌측 트랙볼을 SPI 직접 리스너(`trackball_listener`)로 HID 마우스 리포트 처리
  - 우측 트랙볼로부터 BLE Split 프로토콜(`zmk,input-split`)로 프록시된 입력을 받아 호스트로 전달(`peripheral_trackball_listener`)
- **Peripheral (우측, `modu_right`)**:
  - BLE 무선으로 Central에 키 입력 및 트랙볼 이벤트 전달
  - 우측 트랙볼 센서를 `trackball_split` 노드를 통해 Central로 포워딩

### ③ 듀얼 PMW3610 트랙볼 센서 시스템 (`zmk-pmw3610-driver`)
- **인터페이스**: SPI0 (CS: `P0.21`, IRQ: `P0.17`, CPI: 600)
- **센서 방향 감지 핀 (`orientation-gpios`)**: `P0.08` (Active Low, Pull-Up)
  - 트랙볼 모듈이 장착된 내부/외부 각도에 따라 `P0.08` 신호를 읽어 동적으로 회전 행렬(`alt-rotation-cos-milli = 707`, `alt-rotation-sin-milli = ±707`)과 축 반전(`alt-swap-xy`, `alt-invert-x`, `alt-invert-y`)을 적용

### ④ 커스텀 PWM 숨쉬기 LED 드라이버 (`led_breath.c`)
- 좌/우 3개 채널의 PWM LED 제어
- 블루투스 프로파일(0~2번) 색상 표시, 페어링 대기 상태(빠른 점멸), 분할 키보드 연결 상태 및 부팅 표시

### ⑤ 엄지 클러스터 동적 스캔 드라이버 (`alt_thumb_kscan.c`)
- `P0.08` 핀의 상태에 따라 엄지 클러스터 Row 5의 물리 키 컬럼(Col 0 ↔ Col 2 스왑)을 드라이버 단에서 동적으로 리매핑

---

## 3. 키맵 매트릭스 및 레이어 구성 분석

### ① 67키 물리 매트릭스 (`default_transform`)
- **매트릭스 크기**: 12열 × 6행 (총 67개 바인딩)
- **행 구성**:
  - **Row 0 ~ 3**: 표준 12열 키들 (양손 각 6키씩 48키)
  - **Row 4**: 좌측 3키(`LCTL`, `LALT`, `LGUI`), 우측 3키(`RALT`, `RCTRL`, `INS`)
    - ⚠️ **중요 (플레이스홀더)**: Row 4의 중앙 6개 키(인덱스 51~56, Row 4 Col 3~8)는 물리적으로 스위치가 없으나 ZMK 매트릭스 정렬을 위해 반드시 `&none` 플레이스홀더를 유지해야 합니다.
  - **Row 5 (엄지 클러스터)**: 좌측 3키(Col 0, 1, 2) + 우측 4키(Col 6, 7, 8, 9) = 총 7키

### ② 9개 레이어 구조 분석
| 레이어 | 이름 | 진입 방식 | 주요 역할 및 특징 |
| :---: | :--- | :--- | :--- |
| **Layer 0** | `default_layer` | 기본값 / `to_win` | **Windows 기본 모드** (우상단 Backspace, 엄지 한/영, Space, MO 1, Delete) |
| **Layer 1** | `lower_layer` | 엄지 `MO 1` 홀드 | **Windows 보조 레이어** (F1~F12, 표준 기호열, 방향키, 마우스 클릭, BT 제어) |
| **Layer 2** | `layer_2` | Lower에서 `MO 2` 홀드 | **부트로더 레이어** (5, 6번 누르면 UF2 펌웨어 플래싱 모드 진입) |
| **Layer 3** | `mac_layer` | `to_mac` | **Mac 기본 모드** (왼쪽 ⌥ Opt, ⌘ Cmd 및 대칭 엄지 배치) |
| **Layer 4** | `mac_lower_layer` | 엄지 `MO 4` 홀드 | **Mac 보조 레이어** (F1~F12, 기호/편집키, 마우스 클릭) |
| **Layer 5** | `mac_media_layer` | `mac_to_media` | **Mac 미디어 기본 모드** (엄지 MO 6 매핑) |
| **Layer 6** | `mac_media_lower_layer` | 엄지 `MO 6` 홀드 | **Mac 미디어 Lower** (최신 macOS 밝기, Spotlight, 마이크 음성입력, 볼륨) |
| **Layer 7** | `win_media_layer` | `win_to_media` | **Windows 미디어 기본 모드** (엄지 MO 8 매핑) |
| **Layer 8** | `win_media_lower_layer` | 엄지 `MO 8` 홀드 | **Windows 미디어 Lower** (멀티미디어 제어 키 매핑) |

### ③ 엄지 클러스터 배치
- **Windows (`default_layer` / `win_media_layer`)**:
  - 좌측 엄지: `[한/영 (&kp LANG1)]` | `[Space]` | `[Lower (&mo 1 / &mo 8)]`
  - 우측 엄지: `[한/영 (&kp LANG1)]` | `[Space]` | `[Delete (&kp DELETE)]` | `[B]`
- **Mac (`mac_layer` / `mac_media_layer`)**:
  - 좌측 엄지: `[한/영 (&kp LANG1)]` | `[Space]` | `[Lower (&mo 4 / &mo 6)]`
  - 우측 엄지: `[Lower (&mo 4 / &mo 6)]` | `[Space]` | `[Delete (&kp DELETE)]` | `[B]`

### ④ Lower 레이어 표준 기호 및 마우스 포인팅 매핑
- **오른손 상단 기호 연속열**:
  - `U` 자리: `~ / ` ` `` (`&kp GRAVE`) ➔ 오른손 기호열(`~`, `-`, `=`, `[`, `]`) 완성
  - `I` 자리: `- / _` (`&kp MINUS`)
  - `O` 자리: `= / +` (`&kp EQUAL`)
  - `P` 자리: `[ / {` (`&kp LBKT`)
  - `\` (`BSLH`) 자리: `] / }` (`&kp RBKT`)
- **표준 손 위치 일치 기호**:
  - `ENTER` 자리: 따옴표 `' / "` (`&kp SQT`) ➔ 세미콜론(`;`) 바로 오른쪽 표준 위치와 완벽 일치
  - `RSHFT` 자리: 역슬래시 `\ / |` (`&kp BSLH`)
- **트랙볼 마우스 클릭 (`mkp`)**:
  - `Y`: 휠/중간 클릭 (`&mkp MCLK`)
  - `H`: 우클릭 (`&mkp RCLK`)
  - `N`: 좌클릭 (`&mkp LCLK`)

### ⑤ 최신 macOS 멀티미디어 키 매핑 (`mac_media_lower_layer`)
- `F1` / `F2`: 화면 밝기 감소 (`&kp C_BRI_DN`) / 증가 (`&kp C_BRI_UP`)
- `F3`: Mission Control (`&kp F3`)
- `F4`: Spotlight 통합 검색창 (`&kp C_AC_SEARCH`)
- `F5`: 받아쓰기 / 음성 입력 (`&kp C_VOICE_COMMAND`)
- `F6`: 집중 모드 / 방해금지 (`&kp F6`)
- `F7` ~ `F9`: 이전 트랙 (`&kp C_PREV`), 재생/일시정지 (`&kp C_PP`), 다음 트랙 (`&kp C_NEXT`)
- `F10` ~ `F12`: 음소거 (`&kp C_MUTE`), 볼륨 감소 (`&kp C_VOL_DN`), 볼륨 증가 (`&kp C_VOL_UP`)

### ⑥ 콤보(Combos) 단축키 시스템
엄지 `MO` 키를 누른 상태(Lower 레이어)에서 동시 입력:
- **`X` + `S`**: Windows 기본 모드(`default_layer`) 전환
- **`X` + `A`**: Mac 기본 모드(`mac_layer`) 전환
- **`X` + `F`**: **현재 OS 내에서 F키 모드 ↔ 멀티미디어 모드 상호 토글**
  - Windows F키(Layer 1) ➔ Windows 미디어(Layer 7)
  - Windows 미디어(Layer 8) ➔ Windows F키(Layer 0)
  - Mac F키(Layer 4) ➔ Mac 미디어(Layer 5)
  - Mac 미디어(Layer 6) ➔ Mac F키(Layer 3)
- **`LCTRL(48)` + `5` + `6`**: 키보드 소프트 리셋 (`&sys_reset`)
- **좌측 하단 `MO 2` + `5` or `6`**: USB 부트로더 진입 (`&bootloader`)

---

## 4. 빌드, 패키징 및 검증 파이프라인

### ① GitHub Actions 워크플로우 (`.github/workflows/build.yml`)
1. **`validate` 잡**: 정적 일관성 및 패키징 안전장치 사전 검사
2. **`build` 잡**: ZMK 공식 `build-user-config.yml` 워크플로우를 호출하여 양손 펌웨어 컴파일 (`fallback_binary: hex`)
3. **`package` 잡**:
   - `scripts/package_firmware.py`를 실행하여 컴파일된 Intel HEX를 정규화(`scripts/normalize_hex.py`)
   - 업스트림 `uf2conv.py`로 nRF52840 패밀리 ID(`0xADA52840`)를 지정해 UF2 변환
   - `scripts/verify_uf2.py`로 UF2 매직 넘버, 블록 수, 메모리 영역 중복 여부 등을 이중 검증 후 `modu_left.uf2`, `modu_right.uf2` 아티팩트 업로드
4. **CI/CD 트리거 조건 (`paths`)**:
   - 실제 펌웨어 빌드에 영향을 미치는 핵심 파일(`config/**`, `build.yaml`, `.github/workflows/build.yml`) 변경 시에만 빌드 실행.
   - 문서(`*.md`), 이미지/다이어그램(`docs/**`), 라이선스 파일, 유틸리티 스크립트(`scripts/generate_layer_svgs.py`) 변경 시에는 불필요한 빌드가 실행되지 않도록 최적화됨.

### ② 필수 로컬 검증 명령어
코드나 키맵을 변경했을 때는 반드시 다음 명령어로 무결성을 확인해야 합니다:
```bash
# 1. 정적 무결성 검증 (67개 바인딩, transform 좌표, 플레이스홀더 인덱스)
python3 scripts/validate.py

# 2. Intel HEX 및 UF2 패키징 안전장치 셀프테스트
python3 scripts/selftest.py

# 3. 레이어 SVG XML 문법 유효성 검사
python3 -c "import xml.etree.ElementTree as ET, glob; [ET.parse(f) for f in glob.glob('docs/*.svg')]; print('All SVGs valid XML')"
```

---

## 5. 레이어 SVG 다이어그램 생성 도구 (`generate_layer_svgs.py`)

- **파일 위치**: [`scripts/generate_layer_svgs.py`](scripts/generate_layer_svgs.py)
- **동작 방식**: `config/modu.json`의 기하학적 좌표와 `config/modu.keymap`의 바인딩을 파싱하여 9개 레이어별 시각적 SVG 다이어그램을 자동 렌더링
- **실행 방법**:
  ```bash
  python3 scripts/generate_layer_svgs.py
  # 또는
  ./scripts/generate_layer_svgs.py
  ```

---

## 6. ⚠️ 사용자 필수 준수 규칙 (Critical User Constraints)

1. **`docs/layout-preview.svg` 파일 수정 금지**:
   - 사용자의 명시적 요청에 따라 기존 원본 파일 내용을 **절대로 수정하거나 덮어쓰지 말고 그대로 보존**해야 합니다.
2. **`README.md` 파일 수정 금지**:
   - 원본 소개 문서 상태를 그대로 유지해야 합니다.
3. **레이어 SVG 파일 명명 규칙**:
   - 새로 생성되는 레이어 다이어그램은 `docs/layer-0-default.svg` ~ `docs/layer-8-win-media-lower.svg`로만 관리됩니다.
4. **플레이스홀더 `&none` 키 유지**:
   - Row 4의 51~56번 인덱스는 반드시 `&none`으로 유지되어야 하며, 임의로 다른 키를 할당하거나 삭제해서는 안 됩니다.
