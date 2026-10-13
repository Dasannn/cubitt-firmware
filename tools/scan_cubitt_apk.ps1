param(
    [Parameter(Mandatory = $true)]
    [string]$ApkPath,

    [string]$OutDir = "analysis"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ApkPath)) {
    throw "APK not found: $ApkPath"
}

$resolvedApk = Resolve-Path -LiteralPath $ApkPath
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$apkName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedApk.Path)
$apkName = $apkName -replace "[^A-Za-z0-9_.-]", "_"
$root = Get-Location
$resolvedOutDir = Join-Path $root $OutDir
New-Item -ItemType Directory -Force -Path $resolvedOutDir | Out-Null

$reportPath = Join-Path $resolvedOutDir "cubitt-apk-scan-$apkName-$timestamp.txt"

$terms = @(
    "vita",
    "ai",
    "voice",
    "speech",
    "audio",
    "ota",
    "dfu",
    "firmware",
    "upgrade",
    "update",
    "gatt",
    "uuid",
    "ble",
    "bluetooth",
    "gemini",
    "google",
    "http://",
    "https://",
    ".bin",
    ".fw",
    ".zip",
    ".json"
)

Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Text;

public static class ApkStringScanner
{
    public static List<string> ExtractMatches(byte[] bytes, string[] terms, int maxMatches)
    {
        var matches = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        ScanAscii(bytes, terms, matches, seen, maxMatches);
        ScanUtf16Le(bytes, terms, matches, seen, maxMatches);
        return matches;
    }

    private static void AddIfInteresting(string value, string[] terms, List<string> matches, HashSet<string> seen, int maxMatches)
    {
        if (matches.Count >= maxMatches) return;
        if (value == null) return;
        string clean = value.Trim();
        if (clean.Length < 4) return;

        foreach (var term in terms)
        {
            if (clean.IndexOf(term, StringComparison.OrdinalIgnoreCase) >= 0)
            {
                if (clean.Length > 260) clean = clean.Substring(0, 260) + "...";
                if (seen.Add(clean)) matches.Add(clean);
                return;
            }
        }
    }

    private static void ScanAscii(byte[] bytes, string[] terms, List<string> matches, HashSet<string> seen, int maxMatches)
    {
        var sb = new StringBuilder();
        for (int i = 0; i < bytes.Length; i++)
        {
            byte b = bytes[i];
            if (b >= 32 && b <= 126)
            {
                sb.Append((char)b);
                if (sb.Length > 1024)
                {
                    AddIfInteresting(sb.ToString(), terms, matches, seen, maxMatches);
                    sb.Clear();
                }
            }
            else
            {
                if (sb.Length >= 4) AddIfInteresting(sb.ToString(), terms, matches, seen, maxMatches);
                sb.Clear();
                if (matches.Count >= maxMatches) return;
            }
        }
        if (sb.Length >= 4) AddIfInteresting(sb.ToString(), terms, matches, seen, maxMatches);
    }

    private static void ScanUtf16Le(byte[] bytes, string[] terms, List<string> matches, HashSet<string> seen, int maxMatches)
    {
        var sb = new StringBuilder();
        for (int i = 0; i + 1 < bytes.Length; i += 2)
        {
            byte lo = bytes[i];
            byte hi = bytes[i + 1];
            if (hi == 0 && lo >= 32 && lo <= 126)
            {
                sb.Append((char)lo);
                if (sb.Length > 1024)
                {
                    AddIfInteresting(sb.ToString(), terms, matches, seen, maxMatches);
                    sb.Clear();
                }
            }
            else
            {
                if (sb.Length >= 4) AddIfInteresting(sb.ToString(), terms, matches, seen, maxMatches);
                sb.Clear();
                if (matches.Count >= maxMatches) return;
            }
        }
        if (sb.Length >= 4) AddIfInteresting(sb.ToString(), terms, matches, seen, maxMatches);
    }
}
"@

function Test-ScannableEntry {
    param([string]$Name)

    $lower = $Name.ToLowerInvariant()
    if ($lower -match "\.(png|jpg|jpeg|webp|gif|mp3|wav|ogg|ttf|otf|arsc)$") {
        return $false
    }

    return (
        $lower -match "\.dex$" -or
        $lower -match "\.so$" -or
        $lower -match "\.(json|xml|txt|properties|proto|bin|dat|fw)$" -or
        $lower.StartsWith("assets/") -or
        $lower.StartsWith("res/raw/")
    )
}

Add-Type -AssemblyName System.IO.Compression.FileSystem

$report = New-Object System.Collections.Generic.List[string]
$report.Add("Cubitt APK scan")
$report.Add("APK: $resolvedApk")
$report.Add("Generated: $(Get-Date -Format s)")
$report.Add("")
$report.Add("Terms: $($terms -join ', ')")
$report.Add("")

$zip = [System.IO.Compression.ZipFile]::OpenRead($resolvedApk)
try {
    foreach ($entry in $zip.Entries) {
        if ($entry.Length -le 0) {
            continue
        }

        if (-not (Test-ScannableEntry -Name $entry.FullName)) {
            continue
        }

        if ($entry.Length -gt 120000000) {
            $report.Add("SKIP large entry: $($entry.FullName) ($($entry.Length) bytes)")
            continue
        }

        $stream = $entry.Open()
        try {
            $memory = New-Object System.IO.MemoryStream
            $stream.CopyTo($memory)
            $bytes = $memory.ToArray()
            $matches = [ApkStringScanner]::ExtractMatches($bytes, $terms, 120)

            if ($matches.Count -gt 0) {
                $report.Add("== $($entry.FullName) ==")
                foreach ($match in ($matches | Select-Object -First 120)) {
                    $report.Add($match)
                }
                if ($matches.Count -gt 120) {
                    $report.Add("... truncated $($matches.Count - 120) additional matches")
                }
                $report.Add("")
            }
        } finally {
            $stream.Dispose()
        }
    }
} finally {
    $zip.Dispose()
}

$report | Set-Content -Path $reportPath -Encoding UTF8
Write-Host "Report written to $reportPath"
