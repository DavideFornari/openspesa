# Download new ANAC files and mirror data/raw to Hugging Face.
# Runs weekly from Windows Task Scheduler on the home PC (ANAC blocks cloud runners).
# Setup and troubleshooting: docs/operations.md
Set-Location (Split-Path $PSScriptRoot)
New-Item -ItemType Directory -Force data/logs | Out-Null
$log = "data/logs/sync-anac.log"
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"

"=== $(Get-Date -Format s) start" >> $log
uv run python -m pipeline.ingest.anac sync cig *>> $log
if ($LASTEXITCODE) { "=== FAILED: ANAC download (exit $LASTEXITCODE)" >> $log; exit 1 }
uv run python -m pipeline.publish.raw_mirror *>> $log
if ($LASTEXITCODE) { "=== FAILED: Hugging Face upload (exit $LASTEXITCODE)" >> $log; exit 1 }
"=== $(Get-Date -Format s) done" >> $log
