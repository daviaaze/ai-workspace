# Investidor Sardinha YouTube knowledge base

The ingestion script archives public video metadata and Portuguese captions for private local search. It downloads captions only, never video or audio. Each note links cited claims and transcript cues to the source timestamp. Captions can be machine-generated, and videos without Portuguese captions are recorded as gaps rather than reconstructed.

Optional summaries and topic/claim extraction run on the local Ollama service with `qwen3.5:9b` by default. They are unverified descriptions of what the video says—not fact-checks or investment recommendations. No transcript is sent to a cloud model. Full-catalog caption ingestion can run separately from the more compute-intensive summary pass.

## Run

From the workspace root:

```bash
# Small pilot with local summaries
python scripts/ingest_investidor_sardinha.py --limit 3

# Ingest the full public catalog; do not spend local inference time on summaries
python scripts/ingest_investidor_sardinha.py --no-summary

# Summarize a specific video on demand
python scripts/ingest_investidor_sardinha.py --video-id MEQi7c29_L4
```

Future runs only fetch new videos and retry records lacking Portuguese captions. The default run also summarizes available unsummarized captions; `--video-id` restricts work to one video. Use `--refresh` to force selected notes to be regenerated, `--model MODEL` to select another model already installed in Ollama, and `--data-dir PATH` to change the local output directory.

The script requires `nix` with network access to `nixpkgs#yt-dlp`; summaries additionally require a running local Ollama server with the selected model. It never downloads video/audio. Output is written under the ignored `data/investidor-sardinha/` directory:

- `index.md` — catalog, caption status, and summary status.
- `manifest.json` — per-video metadata and incremental-ingestion status.
- `videos/<youtube-id>.md` — optional local summary, themes, claims with timestamp links, and cleaned captions with timestamp links.
- `captions/` — downloaded VTT source captions used to create the notes.

The local captions and notes are excluded from Git because they contain source material. Check financial claims against the linked video and independent primary sources before relying on them.
