$ErrorActionPreference = "Continue"
$listPath = "D:\项目\AI多模态控制台\android\pkglist.txt"
$dest = "C:\Users\22153\AppData\Local\hermes\cache\scratch\pkgcache"

New-Item -ItemType Directory -Force -Path $dest | Out-Null

$lines = Get-Content -Path $listPath -Encoding UTF8
$ok = 0; $fail = 0; $skip = 0

foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $parts = $line -split "`t"
    if ($parts.Count -lt 3) { continue }
    $recipe = $parts[0]; $url = $parts[1]; $fname = $parts[2]
    $out = Join-Path $dest $fname

    if ((Test-Path $out) -and ((Get-Item $out).Length -gt 50000)) {
        Write-Output ("复用 {0} ({1:N0} KB)" -f $fname, ((Get-Item $out).Length / 1KB))
        $skip++; continue
    }

    Write-Output ("下载 {0} ..." -f $fname)
    $done = $false
    for ($i = 1; $i -le 3 -and -not $done; $i++) {
        try {
            Invoke-WebRequest -Uri $url -OutFile $out -TimeoutSec 600 -UseBasicParsing
            if ((Test-Path $out) -and ((Get-Item $out).Length -gt 50000)) {
                Write-Output ("   OK {0:N0} KB" -f ((Get-Item $out).Length / 1KB))
                $done = $true; $ok++
            }
        } catch {
            Write-Output ("   第 {0} 次失败: {1}" -f $i, $_.Exception.Message)
            Start-Sleep -Seconds 2
        }
    }
    if (-not $done) { $fail++; if (Test-Path $out) { Remove-Item $out -Force } }
}

Write-Output ""
Write-Output ("下载 {0} 个，复用 {1} 个，失败 {2} 个" -f $ok, $skip, $fail)
Get-ChildItem $dest -File | Select-Object Name, @{n='KB';e={[math]::Round($_.Length/1KB)}} | Format-Table -AutoSize
