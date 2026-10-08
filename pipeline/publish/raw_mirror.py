"""Mirror data/raw to the Hugging Face dataset openspesa/raw-mirror.

Needs a write token: run `hf auth login` once. Usage: uv run python -m pipeline.publish.raw_mirror
Unchanged files are skipped and remote files are never deleted.
"""

from huggingface_hub import upload_folder

from pipeline.ingest.anac import DATA_DIR

REPO_ID = "openspesa/raw-mirror"


def main() -> None:
    commit = upload_folder(
        repo_id=REPO_ID,
        repo_type="dataset",
        folder_path=DATA_DIR / "raw",
        ignore_patterns=["*.part"],  # unfinished downloads
        commit_message="Mirror ANAC raw files",
    )
    print(commit)


if __name__ == "__main__":
    main()
