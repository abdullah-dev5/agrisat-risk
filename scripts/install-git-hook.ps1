# Installs prepare-commit-msg hook to block Cursor co-author on this repo.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$hookSrc = Join-Path $root "scripts\prepare-commit-msg"
$hookDst = Join-Path $root ".git\hooks\prepare-commit-msg"

if (-not (Test-Path (Join-Path $root ".git"))) {
  Write-Error "Not a git repository: $root"
}

Copy-Item -Force $hookSrc $hookDst
Write-Host "Installed: $hookDst"
Write-Host "Future commits on this repo will not include cursoragent co-author lines."
