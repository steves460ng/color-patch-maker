# Color Patch Maker

사용자가 정한 규칙대로 CMYK 패치를 만들어 인쇄용 PDF로 출력하는 데스크톱 도구입니다. 작업자는 인쇄된 패치를 실물 견본과 비교해 가장 가까운 CMYK 값을 고릅니다.

- **두 채널 격자:** 기준 CMYK 주변에서 두 채널을 일정 간격으로 바꾼 패치
- **시작·끝 보간:** 두 CMYK 값 사이를 패치 수만큼 균등하게 채운 패치
- 모든 CMYK 값은 정수이며, 한 PDF는 한 페이지입니다. 패치가 넘치면 단일 페이지 PDF 여러 개로 나눕니다.
- 데스크톱 GUI와 명령줄(CLI)을 같은 엔진으로 제공하고, Windows 실행 파일로 배포합니다.

## 현재 상태

구현 진행 상태와 검증 결과는 [진행상황](docs/PROGRESS.md)을 참조하세요.

## 문서

- [설계 문서](docs/DESIGN.md): 기능, 화면 구성, 구조, 개발 순서, 수용 기준. 유일한 설계 기준입니다.
- [화면 시안](docs/ui/mockup.html): 브라우저로 열면 동작하는 GUI 시안입니다.
- [진행상황](docs/PROGRESS.md): 상태와 검증 결과를 기록합니다.
- [작업 규칙](AGENTS.md): 개발을 시작하기 전에 읽습니다.

## 개발 및 실행

Python 3.12에서 저장소 루트 기준으로 실행합니다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q
.venv/bin/cpm grid --cmyk 40 70 20 0 --channels CM --step 1 --cols 7 --rows 7
.venv/bin/cpm ramp --from 40 70 20 0 --to 30 75 30 5 --count 11
.venv/bin/cpm verify output/C40_M70_Y20_K0_CM_s1.pdf output/C40_M70_Y20_K0_CM_s1.json
```

Windows에서는 `.venv/bin/` 대신 `.venv/Scripts/`를 사용합니다.
공통 옵션은 `--paper W H`, `--margin`, `--gap`, `--patch-size`, `--out-dir`입니다.
결과는 stdout JSON, 경고·오류는 stderr이며 오류 종료 코드는 2입니다.
PDF마다 같은 이름의 JSON을 저장하고 기존 이름과 충돌하면 묶음에 `_v2` 등을 붙입니다.

## 콘솔 실행 파일 빌드

```sh
.venv/bin/python -m PyInstaller --noconfirm --clean --onefile --name cpm --paths . --specpath build scripts/cpm_entry.py
```

빌드한 운영체제용 실행 파일이 `dist/`에 생성됩니다. Windows 배포 파일은 Windows에서 빌드해야 합니다.

엔진의 `layout()`은 PDF를 쓰지 않고 장 목록, 패치 ID·정수 CMYK·라벨·mm 사각형을 반환합니다.
`input_errors(mode, **입력)`은 기존 검사 규칙으로 칸별 오류 사전을 반환합니다(예: `cmyk.0`, `paper.0`, `cols`). 여러 칸에 걸친 레이아웃 오류는 `layout()`이 보고합니다.
`output_names(document)`는 충돌 처리 전 PDF 이름 목록을, `page_header(document, page)`는 기존 장 헤더 문구를 반환합니다.
좌표 원점은 용지 왼쪽 아래입니다. `engine.pdf.export()`는 이 데이터를 출력하고 즉시 역검사합니다.
`verify`는 이 도구가 생성한 PDF와 매니페스트 쌍의 저장값을 검증합니다.
`engine.pdf.preview_paths(document, out_dir)`는 파일을 쓰지 않고 충돌을 반영한 PDF·JSON 경로 목록을 반환합니다. export()와 같은 후보 이름 규칙을 쓰지만 경로를 예약하지 않으므로 실제 생성 이름은 export() 반환값을 따르세요.

## 데스크톱 화면

```sh
.venv/bin/python -m color_patch_maker.gui
```

화면에서 입력 검사, 엔진 기반 미리보기, 장 넘김, 요약·파일명 표시와 패치 선택을 사용할 수 있습니다. 저장 폴더를 선택하거나 입력한 뒤 **PDF 만들기** 또는 Enter로 출력합니다. 입력 오류가 없고 폴더가 존재할 때만 실행됩니다. 생성·역검사는 백그라운드에서 진행하며 그동안 입력과 창 닫기를 잠급니다. 완료 후 실제 파일 목록과 역검사 결과를 확인하고 **폴더 열기**로 이동할 수 있습니다.

폴더와 공통 레이아웃은 다음 실행에 복원되며 CMYK·방식별 입력은 복원하지 않습니다. 설정은 Qt의 사용자별 설정 위치에 저장됩니다.

화면 없는 GUI 검사 및 캡처:

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui.py tests/test_gui_connect.py tests/test_gui_output.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/capture_gui.py
```
