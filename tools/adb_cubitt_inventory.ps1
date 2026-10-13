param(
    [string]$OutDir = "analysis"
)

$ErrorActionPreference = "Stop"

$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $adb)) {
    throw "adb not found at $adb"
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outRoot = Join-Path (Get-Location) $OutDir
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$reportPath = Join-Path $outRoot "cubitt-phone-inventory-$timestamp.txt"

function Add-Section {
    param(
        [System.Collections.Generic.List[string]]$Report,
        [string]$Title,
        [string[]]$Lines
    )

    $Report.Add("")
    $Report.Add("== $Title ==")
    foreach ($line in $Lines) {
        $Report.Add($line)
    }
}

Write-Host "Checking connected Android devices..."
$devices = & $adb devices
$deviceRows = $devices | Select-Object -Skip 1 | Where-Object { $_ -match "\bdevice$" }
if (-not $deviceRows) {
    throw "No Android phones connected through ADB. Connect the phone, authorize USB debugging, and run again."
}

$report = New-Object System.Collections.Generic.List[string]
$report.Add("Cubitt phone inventory")
$report.Add("Generated: $(Get-Date -Format s)")

Add-Section -Report $report -Title "adb devices" -Lines $devices

$phoneProps = & $adb shell getprop
Add-Section -Report $report -Title "phone getprop highlights" -Lines ($phoneProps | Select-String -Pattern "ro.product|ro.build.version|ro.miui|ro.serial|manufacturer|model" | ForEach-Object { $_.Line })

$packages = & $adb shell pm list packages
$matches = $packages | Select-String -Pattern "cubitt|wear|watch|fit|viva" | ForEach-Object { $_.Line }
Add-Section -Report $report -Title "package matches" -Lines $matches

$knownPackages = @(
    "com.cubittpros.wear",
    "com.Cubitt.wear",
    "com.local.cubittgeminibridge"
)

foreach ($packageName in $knownPackages) {
    $packageExists = $packages | Select-String -SimpleMatch "package:$packageName"
    if (-not $packageExists) {
        continue
    }

    $dump = & $adb shell dumpsys package $packageName
    Add-Section -Report $report -Title "dumpsys package $packageName highlights" -Lines ($dump | Select-String -Pattern "versionName|versionCode|firstInstallTime|lastUpdateTime|installerPackageName|signatures|uses-permission|requested permissions|PackageSignatures|pkgFlags|dataDir|codePath" | ForEach-Object { $_.Line.TrimEnd() })

    $paths = & $adb shell pm path $packageName
    Add-Section -Report $report -Title "pm path $packageName" -Lines $paths
}

$bluetooth = & $adb shell dumpsys bluetooth_manager
Add-Section -Report $report -Title "bluetooth manager highlights" -Lines ($bluetooth | Select-String -Pattern "Cubitt|VIVA|Viva|CUBITT|connected|Bonded|address|name" | ForEach-Object { $_.Line.TrimEnd() })

$report | Set-Content -Path $reportPath -Encoding UTF8
Write-Host "Report written to $reportPath"
