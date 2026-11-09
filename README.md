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
좌표 원점은 용지 왼쪽 아래입니다. `engine.pdf.export()`는 이 데이터를 출력하고 즉시 역검사합니다.
`verify`는 이 도구가 생성한 PDF와 매니페스트 쌍의 저장값을 검증합니다.
