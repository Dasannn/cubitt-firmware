param(
    [string]$OutDir = "analysis",
    [string]$Pattern = "cubitt|vita|kriki|ai|voice|speech|azure|ota|dfu|firmware|upgrade|ble|bluetooth|gatt|uuid|http|https|bin|fw|zip|creek",
    [int]$DurationSeconds = 0
)

$ErrorActionPreference = "Stop"

$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $adb)) {
    throw "adb no encontrado en $adb"
}

$devices = & $adb devices
$deviceRows = $devices | Select-Object -Skip 1 | Where-Object { $_ -match "\bdevice$" }
if (-not $deviceRows) {
    throw "No hay telefonos Android conectados por ADB. Conecta el telefono, acepta USB debugging y vuelve a ejecutar."
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outRoot = Join-Path (Get-Location) $OutDir
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$rawPath = Join-Path $outRoot "cubitt-logcat-raw-$timestamp.txt"
$filteredPath = Join-Path $outRoot "cubitt-logcat-filtered-$timestamp.txt"

Write-Host "Clearing old logcat buffer..."
& $adb logcat -c

Write-Host ""
Write-Host "Recording logcat."
Write-Host "Now reproduce the action on the phone: open Cubitt Pro, connect the watch, enter firmware/software update, and try VITA AI once."
if ($DurationSeconds -gt 0) {
    Write-Host "Capture will stop automatically after $DurationSeconds seconds."
} else {
    Write-Host "Press Ctrl+C here when done."
}
Write-Host "Raw log: $rawPath"
Write-Host "Filtered log: $filteredPath"
Write-Host ""

if ($DurationSeconds -gt 0) {
    $process = Start-Process -FilePath $adb -ArgumentList @("logcat", "-v", "time", "*:V") -NoNewWindow -RedirectStandardOutput $rawPath -PassThru
    Start-Sleep -Seconds $DurationSeconds
    if (-not $process.HasExited) {
        $process.Kill()
        $process.WaitForExit()
    }

    Select-String -Path $rawPath -Pattern $Pattern | Set-Content -Path $filteredPath -Encoding UTF8
    Write-Host "Capture complete."
    Write-Host "Raw log: $rawPath"
    Write-Host "Filtered log: $filteredPath"
} else {
    & $adb logcat -v time *:V |
        Tee-Object -FilePath $rawPath |
        Select-String -Pattern $Pattern |
        Tee-Object -FilePath $filteredPath
}
