# Windows 빌드와 확인

이 문서는 Windows 10/11 x64와 Windows PowerShell 5.1 이상을 기준으로 합니다.
Windows 실행 파일은 Windows에서 빌드합니다. Linux 빌드는 설정 점검용이며 Windows 검증을 대신하지 않습니다.

## 1. 준비 확인

[Python 3.12.10 다운로드](https://www.python.org/downloads/release/python-31210/)에서 **Windows installer (64-bit)**를 설치하세요. 설치 옵션에서 Python Launcher(`py`)를 포함합니다. [Git for Windows](https://git-scm.com/download/win)도 설치한 뒤 새 PowerShell을 엽니다.

```powershell
py -3.12 --version
py -3.12 -c "import struct; print(struct.calcsize(chr(80)) * 8)"
git --version
```

`Python 3.12.x`, `64`, Git 버전이 나와야 합니다. 다른 Python 버전만 있어도 3.12 x64를 별도로 설치할 수 있습니다.

## 2. 저장소 받기·갱신

처음 받거나 이미 받은 폴더를 갱신할 때 다음 명령을 실행합니다. 기존 폴더는 수정 사항이 없는지 확인하세요. 수정 파일이 있으면 아래 코드는 중단합니다.
기본은 `main`입니다. 검토 중인 PR 브랜치를 빌드할 때만 `$BuildRef`를 그 브랜치 이름으로 바꿉니다.

```powershell
$BuildRef = 'main'
if (-not (Test-Path .\color-patch-maker)) {
    git clone https://github.com/steves460ng/color-patch-maker.git
    if ($LASTEXITCODE -ne 0) { throw '저장소 받기 실패' }
}
Set-Location .\color-patch-maker
if (git status --porcelain) { throw '수정 파일을 먼저 커밋하거나 별도 보관하세요.' }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw '갱신 실패' }
git switch $BuildRef
if ($LASTEXITCODE -ne 0) { throw '브랜치 전환 실패' }
git pull --ff-only origin $BuildRef
if ($LASTEXITCODE -ne 0) { throw '최신 버전 받기 실패' }
git rev-parse HEAD
```

이미 저장소 안에 있다면 먼저 `Set-Location ..`로 부모 폴더로 이동한 뒤 실행하세요.

## 3. 빌드

저장소 루트에서 실행합니다. 가상환경 활성화나 시스템 실행 정책 변경은 필요 없습니다. `-ExecutionPolicy Bypass`는 이 PowerShell 프로세스에만 적용됩니다. 조직 정책으로 막힌 PC는 관리자에게 허용 방법을 확인하세요.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
if ($LASTEXITCODE -ne 0) { throw '빌드 실패: 위 단계별 오류를 확인하세요.' }
```

Python 3.12 x64 확인 → `.venv-build` 생성 → 고정 의존성 설치 → 전체 offscreen 테스트 → 콘솔·GUI 빌드를 순서대로 실행합니다. 실패하면 그 단계에서 멈춥니다. 재실행하면 기존 build/dist의 같은 앱 빌드 결과는 갱신되므로 배포본은 별도로 보관하세요. 앱이 생성한 PDF는 이 스크립트가 삭제하지 않습니다.

정상 출력 예시(경로와 테스트 수는 버전에 따라 달라질 수 있음):

```text
414 passed ...
빌드 완료 (실행 검증은 check_windows.ps1 및 GUI 수동 확인 필요)
C:\work\color-patch-maker\dist\cpm\cpm.exe
C:\work\color-patch-maker\dist\ColorPatchMaker\ColorPatchMaker.exe
```

두 앱은 **onedir 폴더 배포**입니다. GUI의 onefile 압축 해제에 따른 시작 지연을 피하고 파일 구성을 확인하기 쉽게 했습니다. CLI도 같은 배포 방식을 사용합니다.

- 콘솔: `dist\cpm\cpm.exe` — `dist\cpm` 폴더 전체를 옮깁니다.
- GUI: `dist\ColorPatchMaker\ColorPatchMaker.exe` — `dist\ColorPatchMaker` 폴더 전체를 옮깁니다.
- 각각의 `_internal` 폴더를 포함해야 합니다. EXE만 복사하거나 두 `_internal`을 합치지 마세요.
- ReportLab 데이터(글꼴 포함), pikepdf 네이티브 라이브러리는 PyInstaller 수집 설정/훅으로 포함합니다. GUI는 Qt 훅과 플랫폼 플러그인 수집을 사용하며 Windows 빌드는 `qwindows.dll` 포함 여부를 확인합니다.
- 아이콘: `color_patch_maker\gui\resources\app.ico`(16~256px 7개 크기)를 두 EXE 파일 아이콘과 GUI 창·작업 표시줄 아이콘에 씁니다. 빌드 스크립트는 빌드 전에 아이콘 파일을, 빌드 후에 GUI 폴더 안의 아이콘 포함 여부를 확인합니다. 아이콘을 바꿀 때는 같은 경로의 파일만 교체하고 다시 빌드합니다.
- `pefile`, `pywin32-ctypes`는 Windows PyInstaller의 빌드 의존성으로 버전을 고정했습니다. 앱 런타임 의존성 추가는 없습니다.

## 4. 빌드 후 CLI 확인

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_windows.ps1
if ($LASTEXITCODE -ne 0) { throw '실행 확인 실패: 위 오류와 진단 폴더를 확인하세요.' }
```

Python을 호출하지 않고 `cpm.exe`만 실행합니다. 새 `%TEMP%\cpm-check-<고유값>` 폴더에서 기본 격자·보간·50mm 지정 분할 출력을 만들고 모든 PDF/JSON 쌍을 역검사합니다. `40.5`와 `40.0`은 오류 종료 코드 2와 파일 미생성을 확인합니다. 기존 파일은 건드리지 않고 결과를 남깁니다.

정상 출력의 마지막 부분:

```text
확인 완료: grid/ramp/split, PDF 4 개 역검사, 소수 입력 2건 종료 코드 2
결과 폴더: C:\Users\...\AppData\Local\Temp\cpm-check-...
```

소수 검사의 `오류: ...` 출력은 예상된 결과입니다. 마지막 완료 문구와 프로세스 종료 코드 0을 확인하세요. 실패 시 출력된 진단 폴더의 `stdout.txt`, `stderr.txt`에 마지막 실행 출력이 남습니다.

## 5. GUI 실행과 수동 확인

```powershell
Start-Process .\dist\ColorPatchMaker\ColorPatchMaker.exe
```

탐색기에서 EXE를 두 번 클릭해서도 확인하세요. 아래 표에 Windows 버전, 화면 배율, 빌드 커밋과 함께 결과를 적습니다.

| 항목 | 결과(통과/실패/미확인) | 비고 |
| --- | --- | --- |
| Windows 버전·화면 배율·빌드 커밋 | | |
| 빌드 완료, 두 실행 파일과 내부 파일 존재 | | |
| CLI 기본 격자·보간·분할·역검사·소수 거부 | | |
| GUI 창 열림, 별도 콘솔 창 없음 | | |
| 아이콘: 탐색기의 두 EXE, GUI 창 제목 표시줄, 작업 표시줄 | | |
| 격자·보간 미리보기 및 패치 선택 | | |
| 실제 폴더 선택 창으로 저장 폴더 선택 | | |
| PDF 만들기, 생성 중 입력 잠금·창 응답 | | |
| 완료 목록·역검사 통과, 폴더 열기 | | |
| 1024×720, 1600×900에서 알림 가림 없음(기본·입력 오류·생성 중·완료·실패) | | |
| Windows 글꼴·배율에서 두 탭 전환 및 창 크기 변경 | | |
| 종료 후 재실행 시 폴더·레이아웃 복원, CMYK 기본값 | | |
| Python 없는 PC의 CLI 확인 스크립트 통과 | | |
| Python 없는 PC의 GUI 및 실제 PDF 생성 | | |

실패 화면은 존재하지 않는 폴더 입력이나 쓰기 권한 없는 테스트 폴더로 확인하세요. 저장할 중요한 파일이 있는 폴더의 권한은 바꾸지 마세요.

## 6. Python 없는 PC에서 확인

다음 구조를 USB나 ZIP으로 옮깁니다. ZIP은 모두 압축 해제한 다음 실행합니다.

```text
ColorPatchMaker-release/
  cpm/                  (dist/cpm 전체)
  ColorPatchMaker/       (dist/ColorPatchMaker 전체)
  check_windows.ps1     (scripts/check_windows.ps1 복사본)
```

대상 PC에서 이 폴더를 열어 PowerShell로 실행합니다. Python과 소스 저장소는 필요 없습니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\check_windows.ps1 -Cpm .\cpm\cpm.exe
if ($LASTEXITCODE -ne 0) { throw '대상 PC CLI 확인 실패' }
Start-Process .\ColorPatchMaker\ColorPatchMaker.exe
```

위 GUI 수동 목록을 다시 수행합니다. 이 단계가 끝나기 전에는 배포 검증 완료로 기록하지 않습니다.

## 문제 해결과 결과 전달

- Python 버전/아키텍처 오류: `py -0p`로 설치 목록을 확인하고 3.12 x64를 설치하세요. 기존 `.venv-build`가 다른 Python으로 생성됐으면 그 폴더만 삭제하고 다시 빌드합니다.
- 테스트 실패: 실패한 테스트 이름과 traceback 전체를 보내세요. 테스트를 생략해서 빌드하지 마세요.
- 백신/SmartScreen 차단: 이 빌드는 서명하지 않습니다. 차단 알림·파일명·보안 제품 기록을 확인해 조직 관리자에게 전달하세요. 보안 기능 전체를 끄지 마세요.
- 바로가기로 실행하면 실행되지 않음(조사 중): 바탕화면에 EXE를 복사하면 `_internal`이 없어 실행되지 않습니다. EXE를 오른쪽 클릭해 **바로 가기 만들기**로 만든 바로가기(.lnk)를 쓰고, 바로가기 속성의 대상과 시작 위치가 배포 폴더를 가리키는지 확인하세요. 그래도 실행되지 않으면 오류 창 내용을 기록해 주세요.
- Qt 플랫폼 플러그인 오류: GUI `_internal\PySide6\plugins\platforms\qwindows.dll`을 포함해 폴더 전체가 복사됐는지 확인하세요. 다른 Qt 앱의 `QT_PLUGIN_PATH`/`QT_QPA_PLATFORM_PLUGIN_PATH` 환경 변수가 설정됐다면 새 PowerShell에서 해당 값의 영향을 확인하세요. 임의 DLL 다운로드 대신 원본 빌드를 다시 복사하세요.
- 탐색기에 이전 아이콘이 보임: Windows 아이콘 캐시 때문입니다. `dist` 폴더를 다른 이름의 폴더로 복사해 확인하거나, 로그아웃 후 다시 로그인하세요. 창과 작업 표시줄 아이콘이 맞으면 빌드는 정상입니다.
- 실행 중 DLL 오류: x64 Windows인지, 전체 폴더를 복사했는지 먼저 확인하고 오류의 DLL 이름과 화면을 보내세요.
- 보내줄 자료: 위 확인 표, Windows 버전·화면 배율·Python 버전·빌드 커밋, 실패 단계부터 끝까지 PowerShell 출력, GUI 오류 화면, 확인 스크립트 진단 폴더의 stdout/stderr 및 관련 PDF/JSON. 경로의 사용자 이름 등 개인정보는 가려도 됩니다.

Linux에서 수행한 검사와 Windows 미검증 상태는 [PROGRESS.md](PROGRESS.md)에 기록합니다.
