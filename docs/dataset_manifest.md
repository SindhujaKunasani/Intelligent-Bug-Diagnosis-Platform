# Dataset Acquisition Manifest

**Status:** Public Mozilla, Apache and Eclipse datasets have NOT been downloaded in this starter archive. The included `data/demo_synthetic_defects.csv` is entirely synthetic and is for smoke testing only. Do not present it as public-project issue history.

| Source | Dataset URL / Kaggle slug | Version or extraction date | License / permission | Rows imported | Notes |
|---|---|---|---|---:|---|
| Mozilla | To be filled after download | — | Verify before redistribution | 0 | Bugzilla format |
| Apache | To be filled after download | — | Verify before redistribution | 0 | Jira export format |
| Eclipse | To be filled after download | — | Verify before redistribution | 0 | Bugzilla format |

For each downloaded CSV, review its headers and edit `scripts/ingest.py` aliases or prepare a normalized CSV with the fields `source,bug_id,title,description,stack_trace,comments,resolution,status,url`. Import using the commands in the README. Do not assume every Kaggle dataset contains all three sources.
