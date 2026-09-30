# Builds the speech sidecar and the voice trainer into dist/, with SHA256SUMS.
# To test the build in an aircraft app, point that app's CREWMATE_VOICE_DIST at dist/.
param(
    [string]$Version = "0.0.0-dev"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$dist = Join-Path $root "dist"
$work = Join-Path $root "obj-dist"

$sidecarName = "copilot_speech-x86_64-pc-windows-msvc.exe"
$trainerName = "CrewMate-SpeechTrainer.exe"

if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory -Force -Path $dist | Out-Null

Write-Host "[Build] Sidecar $Version" -ForegroundColor Cyan
dotnet publish (Join-Path $root "Sidecar\CopilotSpeech.csproj") -c Release -r win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:EnableCompressionInSingleFile=true -p:Version=$Version `
    -o (Join-Path $work "sidecar")
if ($LASTEXITCODE -ne 0) { throw "[Build] Sidecar build failed" }
Copy-Item (Join-Path $work "sidecar\CopilotSpeech.exe") (Join-Path $dist $sidecarName)

Write-Host "[Build] Trainer $Version" -ForegroundColor Cyan
dotnet build (Join-Path $root "Trainer\SpeechTrainer.csproj") -c Release -p:Version=$Version `
    -o (Join-Path $work "trainer")
if ($LASTEXITCODE -ne 0) { throw "[Build] Trainer build failed" }
Copy-Item (Join-Path $work "trainer\$trainerName") (Join-Path $dist $trainerName)

# Two-space separator is the sha256sum format, so `sha256sum -c` works on it too
$sums = foreach ($name in @($sidecarName, $trainerName)) {
    $hash = (Get-FileHash (Join-Path $dist $name) -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $name"
}
Set-Content -Path (Join-Path $dist "SHA256SUMS") -Value $sums -Encoding ascii
Remove-Item $work -Recurse -Force

Write-Host "[Build] Done:" -ForegroundColor Green
Get-Content (Join-Path $dist "SHA256SUMS")

