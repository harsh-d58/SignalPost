"""Freeze disjoint local cohorts from the official universe, never a scored cache.

Groups known hosts into one split. Unknown ownership/registrable-host relationships
still require an overlap audit before calling any split blind or independent.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import heapq
import json
from pathlib import Path
from urllib.parse import urlsplit

EXPECTED = "b82d6a3e7231d1759a958c282bc4366b80ec2fab8095053d8ed7fa9cd01bc838"


def freeze(universe: Path, output: Path, seed: int, exclusions: list[Path]):
    excluded = set()
    for path in exclusions:
        excluded.update(str(json.loads(line)["organisation_number"]) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    sizes = {"development": 100, "validation": 100, "smoke": 100, "scale": 1100}
    heaps = {key: [] for key in sizes}
    digest = hashlib.sha256()
    total = 0
    with gzip.open(universe, "rb") as source:
        for raw in source:
            digest.update(raw)
            row = json.loads(raw)
            total += 1
            org = str(row["organisation_number"])
            if org in excluded:
                continue
            website = str(row.get("website") or "")
            try:
                host = (urlsplit(website if "://" in website else "https://" + website).hostname or "").lower().removeprefix("www.")
            except ValueError:
                host = ""
            group = host or org
            group_hash = hashlib.sha256(f"{seed}:{group}".encode()).digest()
            split = list(sizes)[int.from_bytes(group_hash[:4], "big") % 4]
            rank = int.from_bytes(hashlib.sha256(f"{seed}:{org}".encode()).digest(), "big")
            item = (-rank, org, host)
            heap = heaps[split]
            if len(heap) < sizes[split]:
                heapq.heappush(heap, item)
            elif item > heap[0]:
                heapq.heapreplace(heap, item)
    if digest.hexdigest() != EXPECTED:
        raise ValueError("universe digest differs from published challenge corpus")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": seed, "universe_rows": total, "universe_content_sha256": digest.hexdigest(),
                "excluded_companies": len(excluded), "splits": {},
                "limitations": "Split isolation covers exact known hosts only. Parent-group and registrable-domain overlap is not independently labeled; these are engineering holdouts, not a precision/recall ground truth."}
    for split, heap in heaps.items():
        chosen = sorted(heap, reverse=True)
        body = "".join(json.dumps({"organisation_number": org}) + "\n" for _, org, _ in chosen)
        path = output / f"{split}-{len(chosen)}.jsonl"
        path.write_text(body, encoding="utf-8")
        manifest["splits"][split] = {"path": path.name, "count": len(chosen), "sha256": hashlib.sha256(body.encode()).hexdigest(),
                                     "known_host_count": sum(bool(h) for _, _, h in chosen)}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("universe", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261109)
    parser.add_argument("--exclude", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    print(json.dumps(freeze(args.universe, args.out, args.seed, args.exclude), indent=2))
