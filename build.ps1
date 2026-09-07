<#
.SYNOPSIS
Select a FlexiHAL firmware, build it and generate a verified UF2.
.EXAMPLE
.\build.ps1
.EXAMPLE
.\build.ps1 -Environment printnc -Version v0.1.0-rc.1
.EXAMPLE
.\build.ps1 -All
.EXAMPLE
.\build.ps1 -Environment printnc -Clean
#>
[CmdletBinding()]
param(
    [string[]]$Environment,
    [string]$Version,
    [switch]$All,
    [switch]$Clean,
    [switch]$List
)

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot
$Prefix = 'f446re_flexi_cnc_'
$Profiles = @(foreach ($line in Get-Content -LiteralPath (Join-Path $RepoRoot 'platformio.ini')) {
    if ($line -match '^\[env:(f446re_flexi_cnc_[^\]]+)\]$') { $Matches[1] }
})
if ($Profiles.Count -eq 0) { throw 'Keine Firmware-Profile in platformio.ini gefunden.' }

function Select-Menu {
    param([string]$Title, [string[]]$Items)
    Write-Host "`n==============================" -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "==============================`n" -ForegroundColor Cyan
    for ($i = 0; $i -lt $Items.Count; $i++) {
        Write-Host "[$($i + 1)] $($Items[$i])"
    }
    Write-Host "[0] Zurueck / Beenden`n"
    while ($true) {
        $choice = Read-Host 'Auswahl'
        if ($null -eq $choice) { return 0 }
        $number = 0
        if ([int]::TryParse($choice, [ref]$number) -and $number -ge 0 -and $number -le $Items.Count) {
            return $number
        }
        Write-Host 'Ungueltige Auswahl.' -ForegroundColor Yellow
    }
}

function Assert-Version {
    param([string]$Value)
    if ($Value -notmatch '^v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?$') {
        throw 'Version muss z.B. v0.1.0-rc.1 oder v0.1.0 sein.'
    }
}

function Invoke-FirmwareBuild {
    param([string[]]$SelectedProfiles, [string]$BuildVersion, [bool]$CleanOnly)
    Assert-Version $BuildVersion
    $python = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $python) { throw 'Python 3.11 oder neuer muss im PATH verfuegbar sein.' }
    foreach ($profile in $SelectedProfiles) {
        $variant = $profile.Substring($Prefix.Length)
        Write-Host "`n==> $variant" -ForegroundColor Cyan
        $buildArgs = @((Join-Path $RepoRoot 'scripts/build.py'), '--environment', $profile, '--version', $BuildVersion)
        if ($CleanOnly) { $buildArgs += '--clean-only' }
        & $python.Source @buildArgs
        if ($LASTEXITCODE -ne 0) { throw "Fehlgeschlagen: $variant (Exitcode $LASTEXITCODE)." }
        if ($CleanOnly) {
            Write-Host "Build-Dateien bereinigt: $variant" -ForegroundColor Green
        } else {
            $uf2 = Join-Path $RepoRoot "outputs\$profile\FlexiHAL-Modulus-$variant-$BuildVersion.uf2"
            if (-not (Test-Path -LiteralPath $uf2 -PathType Leaf)) { throw "UF2 fehlt: $uf2" }
            Write-Host "`nUF2 fertig und geprueft: $uf2" -ForegroundColor Green
        }
    }
}

if ($All -and $Environment) { throw '-All und -Environment koennen nicht kombiniert werden.' }
if ($List) {
    $Profiles | ForEach-Object { $_.Substring($Prefix.Length) }
    return
}
if (-not $Version) {
    $Version = 'v0.1.0-rc.1'
    if (Get-Command git -CommandType Application -ErrorAction SilentlyContinue) {
        try {
            $tag = & git -C $RepoRoot describe --tags --abbrev=0 2>$null
            if ($LASTEXITCODE -eq 0 -and $tag -match '^v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?$') { $Version = $tag }
        } catch {
            Write-Verbose 'Kein Versionstag verfuegbar; verwende die Standardversion.'
        }
    }
}
Assert-Version $Version

if ($All -or $Environment) {
    $selected = if ($All) { $Profiles } else {
        foreach ($item in $Environment) {
            $candidate = if ($item.StartsWith($Prefix)) { $item } else { "$Prefix$item" }
            if ($Profiles -cnotcontains $candidate) { throw "Unbekanntes Profil: $item. Mit -List alle Profile anzeigen." }
            $candidate
        }
    }
    Invoke-FirmwareBuild -SelectedProfiles @($selected | Select-Object -Unique) -BuildVersion $Version -CleanOnly $Clean.IsPresent
    return
}

Write-Host "`nFlexiHAL / Modulus - UF2 Builder" -ForegroundColor Cyan
Write-Host 'MPG=2 | Keypad=0 | ohne Statuslight'
Write-Host 'Hinweis: 5axis_billmill_jerk hat laut Originalkonfiguration drei Achsen.'
while ($true) {
    $action = if ($Clean) { 2 } else { Select-Menu 'Aktion' @('Firmware bauen + UF2 erstellen', 'Build-Dateien bereinigen') }
    if ($action -eq 0) { break }
    $items = @($Profiles | ForEach-Object { $_.Substring($Prefix.Length) }) + @('Alle Profile')
    $choice = Select-Menu 'Firmware auswaehlen' $items
    if ($choice -eq 0) {
        if ($Clean) { break }
        continue
    }
    $selected = if ($choice -eq $items.Count) { $Profiles } else { @($Profiles[$choice - 1]) }
    try {
        if ($action -eq 1) {
            $entered = Read-Host "Release-Version [Enter = $Version]"
            if (-not [string]::IsNullOrWhiteSpace($entered)) {
                Assert-Version $entered.Trim()
                $Version = $entered.Trim()
            }
        }
        Invoke-FirmwareBuild -SelectedProfiles $selected -BuildVersion $Version -CleanOnly ($action -eq 2)
    } catch {
        Write-Host "`n$($_.Exception.Message)" -ForegroundColor Red
    }
    $null = Read-Host 'Enter zum Fortfahren'
}
