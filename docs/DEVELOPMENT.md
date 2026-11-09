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

- 기본 제공 템플릿: `--template 기본|카드|default|card`. 명시한 레이아웃 옵션이 템플릿 값보다 우선합니다. 사용자 템플릿은 GUI에서만 사용합니다.
- 공통 옵션: `--paper W H`, `--margin`, `--gap`, `--patch-size`, `--out-dir`.
- 결과는 표준 출력 JSON, 경고·오류는 표준 오류로 나갑니다. 오류 종료 코드는 2입니다.
- PDF마다 같은 이름의 JSON 매니페스트를 저장하고, 기존 이름과 충돌하면 묶음 전체에 `_v2` 등을 붙입니다.
- GUI 설정(저장 폴더, 공통 레이아웃, 사용자 템플릿)은 Qt의 사용자별 설정 위치에 저장됩니다. CMYK와 방식별 입력은 저장하지 않습니다.

## 엔진

엔진(`color_patch_maker/engine/`)은 GUI 라이브러리에 의존하지 않습니다. GUI와 CLI는 같은 엔진 결과를 표시하거나 출력합니다.

| 함수 | 역할 |
| --- | --- |
| `template_names()` | 기본 제공 이름 목록(기본, 카드)을 반환합니다. |
| `template_values(name)` | 기본 제공 레이아웃 사본을 반환합니다. default/card 별칭도 받으며 값은 engine/templates.py 한 곳에 정의합니다. |
| `validate_template(values)` | 색·방식 입력 없이 기존 layout()의 1×1 검사로 레이아웃을 검증하고 정규화합니다. 실제 입력의 라벨·칸 수 제약은 layout()이 별도로 검사합니다. |
| `layout(mode, **입력)` | PDF를 쓰지 않고 장 목록과 패치 ID·정수 CMYK·라벨·mm 사각형을 반환합니다. 좌표 원점은 용지 왼쪽 아래입니다. |
| `input_errors(mode, **입력)` | 기존 검사 규칙으로 칸별 오류를 반환합니다(예: `cmyk.0`, `paper.0`, `cols`). 여러 칸에 걸친 레이아웃 오류는 `layout()`이 보고합니다. |
| `patch_label(patch)` | CMYK 한 줄과 기준색/시작/끝 표시를 반환합니다. 패치 ID는 인쇄하지 않습니다. |
| `output_names(document)` | 충돌 처리 전 PDF 이름 목록을 반환합니다. |
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

기본 제공 이름·별칭과 상태 표시용 "사용자 설정"은 사용자 템플릿 이름으로 쓸 수 없습니다. 사용자 템플릿은 QSettings의 `layout_templates` JSON 사전에 레이아웃 키만 저장합니다. 손상된 항목은 개별적으로 건너뛰고 알립니다. GUI는 숫자 값이 같은 템플릿을 표시하며 같은 값을 가진 이름이 여럿이면 현재 선택을 우선하고, 그 다음 기본 제공·저장 순서로 고릅니다.


## 출력 형식과 역검사

여백 안쪽 전체를 패치·6mm 라벨 영역에 사용하며 헤더 공간은 없습니다. `page_header()`는 제거했습니다. 라벨에는 CMYK와 기준색 ` *`·시작 ` >`·끝 ` <`만 표시하고 ID·장 번호는 매니페스트와 GUI에 남깁니다. 글꼴은 Helvetica이며 엔진이 패치 폭에 맞춰 최대 7pt에서 `MIN_LABEL_PT`(4.5pt)까지 줄입니다. GUI는 엔진의 `label`과 `label_font_pt`를 그대로 사용합니다.

새 매니페스트는 **schema_version 2**입니다. 키 구조는 같지만 라벨 문구·허용 크기·헤더 유무의 출력 계약이 바뀌어 이전 출력과 구분합니다. 버전 2의 verify는 PDF 전체 텍스트의 순서·개수가 매니페스트 및 CMYK로부터 만든 라벨과 같은지 검사하므로 추가 헤더·빠진 중복 라벨도 거부합니다. Helvetica 글꼴, 폭에 맞춘 글자 크기, 폭 초과, 라벨 위치·검정색도 확인합니다. 기존 DeviceCMYK 패치 값·좌표·용지·단일 페이지 검사도 유지합니다.

버전 1의 기존 PDF/매니페스트는 기존 검사를 유지하여 계속 확인할 수 있습니다. 새 출력은 항상 버전 2로 생성하고 알 수 없는 버전은 거부합니다. 카드 템플릿은 85.6×54mm, 여백 2mm, 간격 1mm, 패치 18mm입니다.
