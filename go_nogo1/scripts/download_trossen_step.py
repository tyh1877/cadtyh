"""Download the public official Interbotix solid STEP calibration files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


MODELS = {
    "px100": "PincherX-100", "px150": "PincherX-150",
    "rx150": "ReactorX-150", "rx200": "ReactorX-200",
    "vx250": "ViperX-250", "vx300": "ViperX-300", "vx300s": "ViperX-300s",
    "wx200": "WidowX-200", "wx250": "WidowX-250", "wx250s": "WidowX-250s",
}
BASE = "https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications/"


def download(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": "GoNoGo1-research-audit/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    path.write_bytes(payload)
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for slug, model in MODELS.items():
        page_url = urllib.parse.urljoin(BASE, f"{slug}.html")
        page_request = urllib.request.Request(page_url, headers={"User-Agent": "Mozilla/5.0 GoNoGo1Research"})
        with urllib.request.urlopen(page_request, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
        match = re.search(r'href="([^\"]+\.zip)"', html, flags=re.I)
        if not match:
            raise RuntimeError(f"No STEP zip linked from {page_url}")
        zip_url = urllib.parse.urljoin(page_url, match.group(1))
        zip_path = args.output_dir / f"{slug}.zip"
        payload = download(zip_url, zip_path)
        extract_dir = args.output_dir / slug
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
        steps = sorted([*extract_dir.rglob("*.step"), *extract_dir.rglob("*.stp")])
        rows.append({
            "slug": slug, "dataset_name": model, "manufacturer": "Trossen Robotics",
            "documentation_url": page_url, "download_url": zip_url,
            "downloaded_utc": datetime.now(timezone.utc).isoformat(),
            "zip_sha256": hashlib.sha256(payload).hexdigest(), "zip_bytes": len(payload),
            "step_file_count": len(steps), "step_files": ";".join(str(x.resolve()) for x in steps),
        })
        print(f"{model}: {len(steps)} STEP files", flush=True)
    with (args.output_dir / "source_manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    main()
