#!/usr/bin/env python3
"""Download CRED-1 credibility dataset and seed aiw's source reputation system.

CRED-1 provides credibility scores for 2,673 domains — fake news sites,
conspiracy domains, unreliable sources, etc. It's updated weekly.

Usage:
    python scripts/download_cred1.py              # Download + seed
    python scripts/download_cred1.py --force      # Force re-download
    python scripts/download_cred1.py --dry-run    # Download but don't seed
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.request import urlretrieve

CRED1_URL = "https://raw.githubusercontent.com/aloth/cred-1/main/data/cred1_current.json"
CACHE_PATH = Path.home() / ".ai-workspace" / "cred1_current.json"


def download() -> Path:
    """Download the latest CRED-1 dataset."""
    print(f"📥 Downloading CRED-1 dataset from {CRED1_URL}")
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(CRED1_URL, str(CACHE_PATH))
    print(f"   Saved to {CACHE_PATH}")
    return CACHE_PATH


def seed(path: Path) -> int:
    """Load CRED-1 into aiw's database."""
    from ai_workspace.sources import SourceReputationService

    svc = SourceReputationService()
    svc.initialize()

    # CRED-1 seed
    count = svc.seed_cred1(str(path))
    print(f"✅ CRED-1: {count} domains seeded")

    # Manual reliable seed
    reliable = svc.seed_reliable()
    print(f"✅ Reliable manual seed: {reliable} domains")

    # Stats
    stats = svc.stats()
    print(f"\n📊 Database now has {stats['total_domains']} domains")
    print(f"   CRED-1 coverage: {stats['cred1_coverage']}")
    print(f"   Avg score: {stats['avg_score']:.3f}")

    return count + reliable


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download and seed CRED-1 dataset")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    parser.add_argument("--dry-run", action="store_true", help="Download but don't seed DB")
    args = parser.parse_args()

    if args.force or not CACHE_PATH.exists():
        path = download()
    else:
        path = CACHE_PATH
        print(f"📦 Using cached CRED-1: {CACHE_PATH}")

    if not args.dry_run:
        total = seed(path)
        print(f"\n🎯 Total domains seeded: {total}")
    else:
        print("🔍 Dry run — dataset downloaded but not seeded. Run without --dry-run to seed.")
