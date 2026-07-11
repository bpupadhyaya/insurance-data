"""Shared helpers for building manifest.json entries.

Every published per-domain file gets one manifest entry: which domain it
feeds, where it came from, when it was snapshotted, and a sha256 so the app
can tell whether a freshly-downloaded file actually changed before doing an
atomic swap into content.db (Phase 4).
"""
import hashlib
import json
import os


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def dataset_entry(dataset_id, domain_id, kind, file_name, published_dir,
                   snapshot_date, source_kind, source_name, source_url):
    """source_kind is "auto" (this run's script actually fetched live data)
    or "manual" (passed through from a human-curated seed file, because the
    real source is a PDF/WAF-blocked site with no scriptable API -- see
    scripts/seed_passthrough.py and dotfiles global-memory/personal/
    insurance.md for which sources hit this and why)."""
    full_path = os.path.join(published_dir, file_name)
    return {
        "id": dataset_id,
        "domain_id": domain_id,
        "kind": kind,
        "file": file_name,
        "sha256": sha256_of(full_path),
        "bytes": os.path.getsize(full_path),
        "snapshot_date": snapshot_date,
        "source_kind": source_kind,
        "source_name": source_name,
        "source_url": source_url,
    }
