#!/usr/bin/env python3
"""Validate a corpus of LaTeXML-generated HTML against the scholarly schema
and aggregate the error landscape.

The single-document loop (convert, validate, read each error) does not
scale to arXiv-sized corpora.  This harness runs vnu.jar in JSON mode
over a directory tree (batched, one JVM per batch), normalizes each
message into a category template, and prints a frequency table of
categories plus the worst-offending files.  Categories are what drive
schema work: a category either maps to a model-sanctioned structure the
profile is missing, a conversion bug in latexml-oxide, or a genuinely
invalid input.

Usage:
  ./corpus-validate.py PATH [PATH ...]
      [--schema URL]      (default: the scholarly profile)
      [--jar PATH]        (default: build/dist/vnu.jar)
      [--batch N]         (default: 200 files per JVM)
      [--json OUT]        (dump raw aggregated records for further analysis)
      [--errors-only]     (default: count errors; pass --infos to include infos)

Exit status: 0 when the corpus is clean, 1 when any error was found.
"""

import argparse
import collections
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_JAR = os.path.join(HERE, "build", "dist", "vnu.jar")
DEFAULT_SCHEMA = "http://s.validator.nu/html5-scholarly.rnc"

QUOTED = re.compile(r"“[^”]*”")
NUMS = re.compile(r"\b\d+\b")


def find_html(paths):
    files = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
        else:
            for root, _dirs, names in os.walk(p):
                files.extend(
                    os.path.join(root, n) for n in names if n.endswith(".html")
                )
    return sorted(files)


def run_batch(jar, schema, files):
    cmd = [
        "java", "-jar", jar,
        "--schema", schema,
        "--format", "json",
        "--skip-non-html", "--exit-zero-always",
    ] + files
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # vnu writes the JSON report to stderr
    payload = proc.stderr.strip() or proc.stdout.strip()
    try:
        return json.loads(payload).get("messages", [])
    except json.JSONDecodeError:
        print("warning: undecodable vnu output for batch starting at "
              f"{files[0]}", file=sys.stderr)
        return []


def categorize(message):
    """Collapse a concrete message into its category template."""
    cat = QUOTED.sub("X", message)
    cat = NUMS.sub("N", cat)
    return cat


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--schema", default=DEFAULT_SCHEMA)
    ap.add_argument("--jar", default=DEFAULT_JAR)
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--infos", action="store_true",
                    help="include info-level messages in the aggregation")
    ap.add_argument("--top", type=int, default=40,
                    help="rows to show per table")
    args = ap.parse_args()

    files = find_html(args.paths)
    if not files:
        sys.exit("no .html files found under: " + " ".join(args.paths))
    print(f"validating {len(files)} files against {args.schema}")

    records = []
    for i in range(0, len(files), args.batch):
        batch = files[i:i + args.batch]
        records.extend(run_batch(args.jar, args.schema, batch))
        done = min(i + args.batch, len(files))
        print(f"  ... {done}/{len(files)}", file=sys.stderr)

    if not args.infos:
        records = [m for m in records if m.get("type") == "error"]

    by_category = collections.Counter()
    by_file = collections.Counter()
    samples = {}
    for m in records:
        cat = categorize(m.get("message", ""))
        by_category[cat] += 1
        url = m.get("url", "?")
        by_file[url] += 1
        samples.setdefault(cat, m)

    n_clean = len(files) - len(set(by_file))
    print(f"\n{'=' * 70}")
    print(f"corpus: {len(files)} files, {n_clean} clean, "
          f"{len(set(by_file))} with findings, "
          f"{sum(by_category.values())} messages "
          f"in {len(by_category)} categories")

    print(f"\n-- categories (top {args.top})")
    for cat, n in by_category.most_common(args.top):
        print(f"{n:7d}  {cat}")
        s = samples[cat]
        loc = f"{os.path.basename(s.get('url', '?'))}:{s.get('lastLine', '?')}"
        print(f"         e.g. {loc}: {s.get('message', '')[:140]}")

    print(f"\n-- files (top {min(args.top, len(by_file))})")
    for url, n in by_file.most_common(args.top):
        print(f"{n:7d}  {url}")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump({
                "files": len(files),
                "categories": dict(by_category),
                "by_file": dict(by_file),
                "messages": records,
            }, f, indent=1)
        print(f"\nraw records: {args.json_out}")

    sys.exit(1 if by_category else 0)


if __name__ == "__main__":
    main()
