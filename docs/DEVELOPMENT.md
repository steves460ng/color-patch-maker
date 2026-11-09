# 개발 안내

Color Patch Maker를 소스에서 실행하고 테스트하는 방법, 엔진 구조를 정리합니다. 작업 규칙은 [AGENTS.md](../AGENTS.md), 설계 기준은 [DESIGN.md](DESIGN.md), Windows 실행 파일 빌드는 [BUILD_WINDOWS.md](BUILD_WINDOWS.md)를 따릅니다.

## 개발 환경

Python 3.12에서 저장소 루트 기준으로 실행합니다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install --no-deps -e .
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Windows에서는 `.venv/bin/` 대신 `.venv/Scripts/`를 사용합니다.

## 실행

```sh
# 데스크톱 화면
.venv/bin/python -m color_patch_maker.gui

# 명령줄
.venv/bin/cpm grid --cmyk 40 70 20 0 --channels CM --step 1 --cols 7 --rows 7
.venv/bin/cpm ramp --from 40 70 20 0 --to 30 75 30 5 --count 11
.venv/bin/cpm verify output/C40_M70_Y20_K0_CM_s1.pdf output/C40_M70_Y20_K0_CM_s1.json
```

- 공통 옵션: `--paper W H`, `--margin`, `--gap`, `--patch-size`, `--out-dir`.
- 결과는 표준 출력 JSON, 경고·오류는 표준 오류로 나갑니다. 오류 종료 코드는 2입니다.
- PDF마다 같은 이름의 JSON 매니페스트를 저장하고, 기존 이름과 충돌하면 묶음 전체에 `_v2` 등을 붙입니다.
- GUI 설정(저장 폴더, 공통 레이아웃)은 Qt의 사용자별 설정 위치에 저장됩니다. CMYK와 방식별 입력은 저장하지 않습니다.

## 엔진

엔진(`color_patch_maker/engine/`)은 GUI 라이브러리에 의존하지 않습니다. GUI와 CLI는 같은 엔진 결과를 표시하거나 출력합니다.

| 함수 | 역할 |
| --- | --- |
| `layout(mode, **입력)` | PDF를 쓰지 않고 장 목록과 패치 ID·정수 CMYK·라벨·mm 사각형을 반환합니다. 좌표 원점은 용지 왼쪽 아래입니다. |
| `input_errors(mode, **입력)` | 기존 검사 규칙으로 칸별 오류를 반환합니다(예: `cmyk.0`, `paper.0`, `cols`). 여러 칸에 걸친 레이아웃 오류는 `layout()`이 보고합니다. |
| `output_names(document)` | 충돌 처리 전 PDF 이름 목록을 반환합니다. |
| `page_header(document, page)` | 장 헤더 문구를 반환합니다. PDF와 미리보기가 같은 문구를 씁니다. |
| `engine.pdf.export(document, out_dir)` | PDF와 매니페스트를 만들고 즉시 역검사합니다. 실패하면 그 실행에서 만든 파일만 정리합니다. |
| `engine.pdf.preview_paths(document, out_dir)` | 파일을 쓰지 않고 충돌을 반영한 PDF·JSON 경로를 반환합니다. 경로를 예약하지 않으므로 실제 이름은 `export()` 반환값을 따릅니다. |
| `engine.pdf.verify(pdf, manifest)` | 이 도구가 만든 PDF와 매니페스트 쌍의 저장값·좌표·용지 치수를 검사합니다. |

## 화면 검사와 캡처

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui.py tests/test_gui_connect.py tests/test_gui_output.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/capture_gui.py
```

캡처는 `docs/ui/screens/`에 저장됩니다.

## 실행 파일 설정 점검 (Linux)

Windows 실행 파일은 Windows에서만 만들 수 있습니다. 아래 명령은 Linux에서 빌드 설정이 깨지지 않았는지만 확인합니다.

```sh
.venv/bin/python -m PyInstaller --noconfirm --clean cpm.spec
.venv/bin/python -m PyInstaller --noconfirm --clean ColorPatchMaker.spec
./dist/cpm/cpm --help
QT_QPA_PLATFORM=offscreen CPM_OFFSCREEN_SMOKE_SETTINGS="$(mktemp -d)" ./dist/ColorPatchMaker/ColorPatchMaker
```

마지막 명령은 임시 설정으로 GUI를 열고 500ms 뒤 정상 종료하는 패키징 검사입니다.

## 아이콘

`color_patch_maker/gui/resources/app.ico`(16~256px)를 두 실행 파일과 GUI 창에 씁니다. README에 쓰는 이미지는 `docs/assets/icon.png`입니다. 아이콘을 바꿀 때는 두 파일을 함께 교체합니다.
