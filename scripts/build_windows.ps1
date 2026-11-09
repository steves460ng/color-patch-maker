#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$stage = '환경 확인'
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "종료 코드 $LASTEXITCODE" }
}
Push-Location (Split-Path $PSScriptRoot -Parent)
$oldPlatform = $env:QT_QPA_PLATFORM
try {
    if ($env:OS -ne 'Windows_NT') { throw 'Windows PowerShell에서 실행하세요.' }
    $stage = 'Python 3.12 x64 확인'
    Invoke-Checked 'py' @('-3.12', '-c', 'import sys, struct; assert sys.version_info[:2] == (3,12) and struct.calcsize(chr(80)) == 8; print(sys.version)')
    $stage = '가상환경 생성'
    Invoke-Checked 'py' @('-3.12', '-m', 'venv', '.venv-build')
    $python = Join-Path (Get-Location) '.venv-build\Scripts\python.exe'
    Invoke-Checked $python @('-c', 'import sys, struct; assert sys.version_info[:2] == (3,12) and struct.calcsize(chr(80)) == 8')
    $stage = '고정 의존성 설치'
    Invoke-Checked $python @('-m', 'pip', 'install', '-r', 'requirements-dev.txt')
    Invoke-Checked $python @('-m', 'pip', 'install', '--no-deps', '--no-build-isolation', '-e', '.')
    Invoke-Checked $python @('-m', 'pip', 'check')
    $stage = '전체 테스트'
    $env:QT_QPA_PLATFORM = 'offscreen'
    Invoke-Checked $python @('-m', 'pytest', '-q')
    $env:QT_QPA_PLATFORM = $oldPlatform
    $stage = 'cpm 콘솔 빌드'
    Invoke-Checked $python @('-m', 'PyInstaller', '--noconfirm', '--clean', 'cpm.spec')
    $stage = 'ColorPatchMaker GUI 빌드'
    Invoke-Checked $python @('-m', 'PyInstaller', '--noconfirm', '--clean', 'ColorPatchMaker.spec')
    foreach ($file in @('dist\cpm\cpm.exe', 'dist\ColorPatchMaker\ColorPatchMaker.exe', 'dist\ColorPatchMaker\_internal\PySide6\plugins\platforms\qwindows.dll')) {
        if (-not (Test-Path $file -PathType Leaf)) { throw "결과 파일 누락: $file" }
    }
    Write-Host '빌드 완료 (실행 검증은 check_windows.ps1 및 GUI 수동 확인 필요)'
    Write-Host (Join-Path (Get-Location) 'dist\cpm\cpm.exe')
    Write-Host (Join-Path (Get-Location) 'dist\ColorPatchMaker\ColorPatchMaker.exe')
} catch {
    Write-Host "실패 [$stage]: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    $env:QT_QPA_PLATFORM = $oldPlatform
    Pop-Location
}
