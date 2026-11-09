#requires -Version 5.1
param([string]$Cpm = (Join-Path $PSScriptRoot '..\dist\cpm\cpm.exe'))
$ErrorActionPreference = 'Stop'
$stage = '실행 파일 확인'
function Invoke-Cpm {
    param([string[]]$Arguments, [int]$Expected = 0)
    # File redirection preserves expected stderr errors under Windows PowerShell 5.1.
    $previousPreference = $ErrorActionPreference
    try {
        # PS 5.1 can wrap native stderr as ErrorRecord even with redirection.
        $ErrorActionPreference = 'Continue'
        & $script:exe @Arguments 1> $script:stdout 2> $script:stderr
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    Get-Content $script:stdout | Write-Host
    Get-Content $script:stderr | Write-Host
    if ($code -ne $Expected) { throw "종료 코드 $code (기대: $Expected)" }
}
try {
    $script:exe = (Resolve-Path $Cpm).Path
    $out = Join-Path ([IO.Path]::GetTempPath()) ('cpm-check-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $out | Out-Null
    $script:stdout = Join-Path $out 'stdout.txt'
    $script:stderr = Join-Path $out 'stderr.txt'
    $total = 0
    foreach ($mode in @('grid', 'ramp', 'split')) {
        $stage = "$mode 출력·역검사"
        $folder = Join-Path $out $mode
        if ($mode -eq 'ramp') {
            $arguments = @('ramp','--from','40','70','20','0','--to','30','75','30','5','--count','11')
        } else {
            $arguments = @('grid','--cmyk','40','70','20','0','--channels','CM','--step','1','--cols','7','--rows','7')
            if ($mode -eq 'split') { $arguments += @('--patch-size','50') }
        }
        Invoke-Cpm -Arguments ($arguments + @('--out-dir',$folder))
        $pdfs = @(Get-ChildItem $folder -Filter '*.pdf')
        if (($mode -ne 'split' -and $pdfs.Count -ne 1) -or ($mode -eq 'split' -and $pdfs.Count -lt 2)) {
            throw "예상하지 못한 PDF 수: $($pdfs.Count)"
        }
        foreach ($pdf in $pdfs) {
            Invoke-Cpm -Arguments @('verify',$pdf.FullName,[IO.Path]::ChangeExtension($pdf.FullName,'.json'))
            $result = Get-Content $script:stdout -Raw | ConvertFrom-Json
            if ($result.verified -ne $true) { throw '역검사 결과가 true가 아닙니다.' }
            $total++
        }
        Write-Host "통과: $mode ($($pdfs.Count) PDF)"
    }
    $stage = '소수 입력 거부'
    foreach ($decimal in @('40.5','40.0')) {
        $bad = Join-Path $out ('invalid-' + $decimal)
        Invoke-Cpm -Arguments @('grid','--cmyk',$decimal,'70','20','0','--out-dir',$bad) -Expected 2
        if (Test-Path $bad) {
            if (@(Get-ChildItem $bad -Recurse -File).Count -ne 0) { throw '잘못된 입력에서 파일이 생성됐습니다.' }
        }
    }
    Write-Host "확인 완료: grid/ramp/split, PDF $total 개 역검사, 소수 입력 2건 종료 코드 2"
    Write-Host "결과 폴더: $out"
} catch {
    Write-Host "실패 [$stage]: $($_.Exception.Message)" -ForegroundColor Red
    if ($out) { Write-Host "진단 폴더: $out" }
    exit 1
}
