
import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

output = Path("data/historical/mozilla.csv")
output.parent.mkdir(parents=True, exist_ok=True)

params = {
    "product": "Core",
    "limit": 100,
    "include_fields": "id,summary,product,component,status,resolution,creation_time",
}

url = (
    "https://bugzilla.mozilla.org/rest/bug?"
    + urllib.parse.urlencode(params)
)

request = urllib.request.Request(
    url,
    headers={
        "User-Agent": "BugDiagnosisResearch/1.0",
        "Accept": "application/json",
    },
)

with urllib.request.urlopen(request, timeout=60) as response:
    bugs = json.load(response)["bugs"]

with output.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "bug_id", "summary", "description",
            "product", "component", "status", "resolution"
        ]
    )
    writer.writeheader()

    for bug in bugs:
        writer.writerow({
            "bug_id": bug.get("id"),
            "summary": bug.get("summary", ""),
            "description": bug.get("summary", ""),
            "product": bug.get("product", ""),
            "component": bug.get("component", ""),
            "status": bug.get("status", ""),
            "resolution": bug.get("resolution", ""),
        })

print(f"Downloaded {len(bugs)} Mozilla bug records")
print(f"Saved to {output}")
