#!/usr/bin/env python3
"""Validate the staged public Loghub extension corpus end to end.

The archives stay in ignored data/; this command streams every selected log line
through the same built-in decoder/mapping/normalization dry-run used by the
existing coverage report and writes a reproducible, hash-bearing report.
"""
import argparse
import json
import os
from pathlib import Path

from measure_coverage import measure

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = (
    ROOT / "data/datasets/bgl/extracted/BGL.log",
    ROOT / "data/datasets/hdfsv1/extracted/HDFS.log",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/coverage-public-40m.json")
    args = parser.parse_args()
    os.chdir(ROOT)
    files = [path for path in EXTENSION if path.exists()]
    files.extend(sorted((ROOT / "data/datasets/hadoop/extracted").rglob("*.log")))
    missing = [str(path) for path in EXTENSION if not path.exists()]
    if not files or missing:
        raise SystemExit("Missing staged public corpora: " + ", ".join(missing))

    results = [measure(path) for path in files]
    summary = {
        "files": len(results),
        "physical_lines": sum(item["physical_lines"] for item in results),
        "metadata_lines": sum(item["metadata_lines"] for item in results),
        "records": sum(item["records"] for item in results),
        "normalized": sum(item["normalized"] for item in results),
        "partial": sum(item["partial"] for item in results),
        "discovery": sum(item["discovery"] for item in results),
        "failed": sum(item["failed"] for item in results),
        "all_raw_lines_hashed": True,
        "synthetic_records": False,
    }
    if summary["records"] < 16_000_000:
        raise SystemExit(f"Extension corpus is unexpectedly small: {summary['records']}")
    payload = {
        "scope": "Full-file public BGL, HDFS_v1 and Hadoop Loghub corpus dry-run",
        "method": "Every physical line is decoded, mapped and normalized or retained as discovery/failed; raw bytes are SHA-256 hashed.",
        "summary": summary,
        "files": results,
        "unavailable_datasets": [],
    }
    output = Path(args.output)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
