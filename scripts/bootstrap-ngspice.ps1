# Workspace-local Ubuntu 24.04 / amd64 ngspice fixture runtime.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$downloadPath = Join-Path $projectRoot '.tools/downloads/ngspice.deb'
$expectedHash = '466c4c06418107ceaa9c9457065b3bb71a9d9dc5ec6fef186d7de9d5208ce8db'
New-Item -ItemType Directory -Force (Split-Path -Parent $downloadPath) | Out-Null
if (-not (Test-Path -LiteralPath $downloadPath)) {
    & curl.exe -fL --max-time 120 'https://archive.ubuntu.com/ubuntu/pool/universe/n/ngspice/ngspice_42+ds-3build1_amd64.deb' -o $downloadPath
    if ($LASTEXITCODE -ne 0) { throw 'ngspice package download failed' }
}
if ((Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
    throw 'ngspice package hash mismatch'
}
Push-Location $projectRoot
try {
    & wsl -e sh -lc 'mkdir -p .tools/ngspice && dpkg-deb -x .tools/downloads/ngspice.deb .tools/ngspice && .tools/ngspice/usr/bin/ngspice --version'
    if ($LASTEXITCODE -ne 0) { throw 'ngspice extraction or runtime check failed; Ubuntu 24.04 amd64 libraries required' }
} finally {
    Pop-Location
}
