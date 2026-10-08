# Operations

## Weekly ANAC sync (home PC)

ANAC blocks cloud servers (see [spikes/anac-runner.md](spikes/anac-runner.md)), so a
Windows scheduled task on the maintainer's PC downloads new files and mirrors `data/raw` to
the Hugging Face dataset [`openspesa/raw-mirror`](https://huggingface.co/datasets/openspesa/raw-mirror).
Everything after raw runs in GitHub Actions.

[`scripts/sync-anac.ps1`](../scripts/sync-anac.ps1):

1. `pipeline.ingest.anac sync cig` downloads every monthly CIG file not yet on disk.
2. `pipeline.publish.raw_mirror` uploads new files and `manifest.jsonl`. Unchanged files
   are skipped.

The log is in `data/logs/sync-anac.log`.

### One-time setup

1. Log in to Hugging Face with a fine-grained token that has write access to the
   `openspesa` organization: `uvx --from huggingface_hub hf auth login`.
2. Run the script once by hand from the repo root and check the log:
   `pwsh -NoProfile -File scripts/sync-anac.ps1`.
3. Register the task (PowerShell, as your normal user, no admin needed):

```powershell
$action = New-ScheduledTaskAction -Execute "pwsh.exe" `
  -Argument "-NoProfile -WindowStyle Hidden -File `"$PWD\scripts\sync-anac.ps1`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 19:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName "OpenSpesa ANAC sync" -Action $action -Trigger $trigger `
  -Settings $settings -Description "Download new ANAC files and mirror them to Hugging Face"
```

The task runs weekly because Task Scheduler has no simple monthly trigger and a run with
nothing new costs one API call. `StartWhenAvailable` runs a missed week as soon as the PC
is back on. It runs only while you are logged in, so no password is stored.

### Check, run now, remove

```powershell
Get-ScheduledTaskInfo "OpenSpesa ANAC sync"    # LastRunTime, LastTaskResult (0 = OK)
Start-ScheduledTask "OpenSpesa ANAC sync"
Unregister-ScheduledTask "OpenSpesa ANAC sync" -Confirm:$false
```

### If it stops

The [`raw-staleness`](../.github/workflows/raw-staleness.yml) workflow checks every Monday
and opens a GitHub issue if `openspesa/raw-mirror` has not changed for 40 days. Check the log,
then run the script by hand. A firewall block shows up as
`got HTML instead of data (blocked by firewall?)`.

To move to another PC, clone the repo, log in to Hugging Face, and **fetch the existing
manifest before the first run**. Otherwise the upload replaces the manifest on Hugging
Face, and its history would survive only in the dataset's git history:

```powershell
uvx --from huggingface_hub hf download openspesa/raw-mirror manifest.jsonl --repo-type dataset --local-dir data/raw
```

Then register the task again. The first run downloads every file again; files identical to
those on Hugging Face upload nothing new.

The dataset card's source is [datasets/raw.md](datasets/raw.md). Upload it again
after editing it.
