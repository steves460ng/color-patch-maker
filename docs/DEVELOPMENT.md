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
| `template_names()` | 기본 제공 내부 식별자 목록(default, card)을 반환합니다. |
| `template_label(id, language="ko")` | 문구 사전에서 표시 이름을 반환합니다. 한국어와 영어를 지원합니다. |
| `template_id(name)` | default/card 또는 기존 한국어 표시 이름을 내부 식별자로 바꿉니다. |
| `template_values(name)` | 기본 제공 레이아웃 사본을 반환합니다. default/card 별칭도 받으며 값은 engine/templates.py 한 곳에 정의합니다. |
| `validate_template(values)` | 색·방식 입력 없이 기존 layout()의 1×1 검사로 레이아웃을 검증하고 정규화합니다. 실제 입력의 라벨·칸 수 제약은 layout()이 별도로 검사합니다. |
| `layout(mode, **입력)` | PDF를 쓰지 않고 장 목록과 패치 ID·정수 CMYK·라벨·mm 사각형을 반환합니다. 좌표 원점은 용지 왼쪽 아래입니다. |
| `input_errors(mode, **입력)` | 기존 검사 규칙으로 칸별 EngineError 객체를 반환합니다(예: `cmyk.0`, `paper.0`, `cols`). 여러 칸에 걸친 레이아웃 오류는 `layout()`이 보고합니다. |
| `patch_label(patch)` | CMYK 한 줄과 기준색/시작/끝 표시를 반환합니다. 패치 ID는 인쇄하지 않습니다. |
| `output_names(document)` | 충돌 처리 전 PDF 이름 목록을 반환합니다. |
| `engine.pdf.export(document, out_dir)` | PDF와 매니페스트를 만들고 즉시 역검사합니다. 실패하면 그 실행에서 만든 파일만 정리합니다. |
| `engine.pdf.preview_paths(document, out_dir)` | 파일을 쓰지 않고 충돌을 반영한 PDF·JSON 경로를 반환합니다. 경로를 예약하지 않으므로 실제 이름은 `export()` 반환값을 따릅니다. |
| `engine.pdf.verify(pdf, manifest)` | 이 도구가 만든 PDF와 매니페스트 쌍의 저장값·좌표·용지 치수를 검사합니다. |

## 화면 검사와 캡처

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui.py tests/test_gui_connect.py tests/test_gui_output.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/capture_gui.py --language ko
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/capture_gui.py --language en
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


## 문구 사전과 오류·경고 (2-6·2-7)

사용자 문구는 `engine/messages.py`의 `KO`·`EN` 사전에 있습니다. `CATALOGS`의 `ko`·`en`은 각각 **123개 키**로, 기존 113개와 언어 선택·저장된 이름 표시·대화 상자 버튼용 10개입니다. 두 언어의 키와 문장 인자가 정확히 같습니다. `t(key, language='ko', **values)`로 완성된 문장 틀에 값을 채웁니다. 없는 키·언어, 누락되거나 불필요한 인자는 KeyError로 즉시 드러납니다. 문장 일부를 붙이지 않고 범위 상한 유무 등은 별도 문장 틀로 둡니다. GUI 생성·갱신·대화 상자와 CLI의 앱 제공 도움말·오류 접두어가 같은 함수를 사용합니다. argparse가 제공하는 기본 도움말 형식은 그대로입니다.

- `EngineError(ValueError)`: `code`(사전 키), `target`(입력/검사 대상), `value`(문제가 된 값), `values`(문장 인자)를 가집니다. `str(error)`는 기존 한국어 문장이며 `error.render(language)`로 언어를 명시할 수 있습니다.
- `Message`: `code`, `values`를 담고 `render(language)`로 경고·안내를 표시합니다. layout()의 고정 경고는 Message 목록이며 GUI의 분할 안내도 같은 구조입니다. CLI에 새 분할 경고는 추가하지 않으며 기존 경고를 영어로 표시합니다.
- `input_errors()`는 칸 이름을 키로, EngineError를 값으로 반환합니다. target도 `cmyk.0` 같은 칸 키로 지정합니다. GUI는 `.render(window.language)`를 표시하고 CMYK 오류 칸에는 기존 짧은 문구를 씁니다.

```python
from color_patch_maker.engine.messages import t, EngineError

text = t('preview.page', current=1, total=8)
error = EngineError('input.integer', target='cmyk.0', value='40.5', name='C')
assert str(error) == error.render('ko')
```

템플릿 콤보 항목 데이터는 기본 제공의 경우 `default`·`card`, 사용자는 `user:<원래 이름>`, 사용자 설정 상태는 None입니다. 표시 이름으로 선택·일치·삭제·되돌리기를 판단하지 않습니다. 새 이름의 예약 목록은 사용자 설정, Custom, 기본, 카드, Default, Card, default, card입니다. 설정 저장 형식(레이아웃 칸과 사용자 템플릿 JSON 사전)은 변경하지 않습니다. 이전에 저장할 수 있었던 Default/Card/Custom 이름은 불러오기에서 보존하며 새 저장은 거부합니다. 이름과 템플릿 값은 번역하지 않습니다. 복원한 Default/Card/Custom은 화면에서만 ` (saved)` 또는 ` (저장)`를 붙여 기본 제공 항목과 구별합니다. 선택·삭제는 원래 사용자 식별자를 사용합니다.

테스트는 사전 밖의 한글 문자열 리터럴(주석·docstring 제외), 키 사용 집합과 인자, 변경 전 오류 문장·CLI 스냅샷, 이전 설정 복원을 검사합니다. `tests/fixtures/messages_ko.json`과 `cli_ko.json`은 2-6 이전 main(`6f4b90b`)에서 얻은 기대값입니다. 한국어 오류 기대값은 `이상로` → `이상으로`만 수정했습니다. `cli_en.json`은 영어 CLI 기대값이며, 기존 9개 사례의 종료 코드·JSON stdout·생성 파일 해시는 그대로이고 도움말과 stderr 문구만 번역했습니다. 인쇄 라벨·파일명·매니페스트 schema_version 2와 내용은 바꾸지 않았습니다.

### 언어 결정과 설정

`gui/language.py`의 `resolve_language(preference, locale_name)`은 저장된 `ko`·`en`을 우선하고, `auto`이면 `QLocale.system().name()`의 언어가 한국어일 때만 `ko`, 나머지는 `en`을 반환합니다. 테스트에서는 로케일 문자열을 주입합니다. QSettings 키 `language`의 기본값은 `auto`이며 알 수 없는 값도 `auto`로 처리합니다.

MainWindow는 위젯을 만들기 전에 언어를 결정하고 `translator(language)`를 `window.t`로 묶어 생성·갱신·대화 상자에 전달합니다. 엔진 객체에는 언어 상태를 저장하지 않습니다. 언어 선택은 즉시 저장하지만 **다음 실행부터 적용**합니다. 실행 중 문구 일부만 바뀌는 일을 피하고 입력·선택·출력 상태를 유지하기 위한 설계 제안 그대로의 동작입니다. 한국어·English 항목은 각 언어의 고유 이름으로 표시합니다.

CLI는 로케일이나 GUI 설정을 읽지 않고 항상 `t(..., 'en')`·`render('en')`을 사용합니다. 오류 접두어는 `error: `이며 JSON stdout·파일명·PDF·매니페스트는 언어와 무관합니다. CP949 메시지 인코딩은 Linux subprocess에서 검사하며 Windows 실제 콘솔 및 JSON 경로 인코딩을 확인한 것은 아닙니다.

앱의 템플릿 대화 상자 버튼은 사전으로 표시합니다. 운영체제가 제공하는 폴더 선택 창과 파일 탐색기의 문구는 운영체제 설정을 따릅니다. 실제 Windows 대화 상자와 글꼴 배치는 수동 확인이 필요합니다. 한국어 캡처는 `docs/ui/screens/`, 영어는 `docs/ui/screens/en/`에 저장합니다.
