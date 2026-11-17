
import csv
import json
import urllib.request
from pathlib import Path

SOURCES = {
    "apache": "apache/airflow",
    "eclipse": "eclipse-platform/eclipse.platform.swt"
}

folder = Path("data/historical")
folder.mkdir(parents=True, exist_ok=True)

for source, repo in SOURCES.items():
    print(f"Downloading {source} issues...")

    url = (
        f"https://api.github.com/repos/{repo}/issues"
        "?state=closed&per_page=100"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BugDiagnosisResearch/1.0",
            "Accept": "application/vnd.github+json"
        }
    )

    try:
        with urllib.request.urlopen(
            request, timeout=60
        ) as response:
            issues = json.load(response)

        records = []

        for issue in issues:
            if "pull_request" in issue:
                continue

            labels = [
                label["name"]
                for label in issue.get("labels", [])
            ]

            # Keep issues explicitly labelled as bugs
            

            records.append({
                "bug_id": str(issue["number"]),
                "summary": issue.get("title", ""),
                "description": issue.get("body") or "",
                "product": repo,
                "component": ", ".join(labels),
                "status": issue.get("state", ""),
                "resolution": (
                    issue.get("state_reason") or ""
                ),
                "source_url": issue.get("html_url", "")
            })

        if not records:
            print(f"No labelled bugs found for {source}")
            continue

        output = folder / f"{source}.csv"

        with output.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file, fieldnames=records[0].keys()
            )
            writer.writeheader()
            writer.writerows(records)

        print(f"Saved {len(records)} bugs to {output}")

    except Exception as error:
        print(f"Error downloading {source}: {error}")

print("Download process finished.")
