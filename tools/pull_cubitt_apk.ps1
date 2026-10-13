param(
    [string]$PackageName = "com.cubittpros.wear",
    [string]$OutDir = "apks"
)

$ErrorActionPreference = "Stop"

$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $adb)) {
    throw "adb no encontrado en $adb"
}

Write-Host "Checking connected Android devices..."
$devices = & $adb devices
$deviceRows = $devices | Select-Object -Skip 1 | Where-Object { $_ -match "\bdevice$" }
if (-not $deviceRows) {
    throw "No hay telefonos Android conectados por ADB. Conecta el telefono, acepta USB debugging y vuelve a ejecutar."
}

$paths = & $adb shell pm path $PackageName
if ($LASTEXITCODE -ne 0 -or -not $paths) {
    throw "No se pudo localizar el paquete $PackageName. Ejecuta tools\adb_cubitt_inventory.ps1 para encontrar el nombre correcto."
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageOut = Join-Path (Join-Path (Get-Location) $OutDir) "$PackageName-$timestamp"
New-Item -ItemType Directory -Force -Path $packageOut | Out-Null

$index = 0
foreach ($line in $paths) {
    if ($line -notmatch "^package:(.+)$") {
        continue
    }

    $remotePath = $Matches[1].Trim()
    $leaf = Split-Path -Leaf $remotePath
    if ([string]::IsNullOrWhiteSpace($leaf)) {
        $leaf = "split-$index.apk"
    }

    $localPath = Join-Path $packageOut $leaf
    Write-Host "Pulling $remotePath -> $localPath"
    & $adb pull $remotePath $localPath
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo adb pull para $remotePath"
    }

    $index += 1
}

Write-Host "APK files written to $packageOut"
Write-Host "Next: .\tools\scan_cubitt_apk.ps1 -ApkPath `"$((Join-Path $packageOut 'base.apk'))`""
