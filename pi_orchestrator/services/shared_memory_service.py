"""
Shared Knowledge Pool — cross-agent memory accumulation.

Cross-agent memory accumulation.
Agents don't message each other — they all read/write to a shared pool.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SHARED_MEMORY_DIR = Path.home() / ".pi" / "agent" / "shared-memory"
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB warning threshold


def _ensure_dir(tag: str) -> Path:
    """Ensure the directory for a tag exists."""
    path = SHARED_MEMORY_DIR / tag
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_fact(
    agent_id: str,
    tag: str,
    fact: str,
    fact_type: str = "dynamic",
    metadata: Optional[dict] = None,
) -> None:
    """Write a fact to the shared knowledge pool.

    Args:
        agent_id: The agent that learned this fact
        tag: Scope tag (e.g., 'frontend', 'infra')
        fact: The fact text
        fact_type: 'static' or 'dynamic'
        metadata: Optional metadata dict
    """
    _ensure_dir(tag)
    path = SHARED_MEMORY_DIR / tag / "knowledge.jsonl"

    entry = {
        "agent_id": agent_id,
        "tag": tag,
        "fact": fact,
        "type": fact_type,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def deduplicate_facts(facts: list[dict]) -> list[dict]:
    """Deduplicate facts. Static wins over dynamic. Later wins over earlier.

    Priority: static > dynamic (within same priority, last wins).
    Deduplication ensures the same fact isn't injected twice.
    """
    seen = set()
    result = []

    sorted_facts = sorted(
        facts, key=lambda f: (0 if f.get("type") == "static" else 1, f.get("timestamp", ""))
    )

    for fact in sorted_facts:
        text = fact.get("fact", "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(fact)

    return result


def read_context(
    tags: list[str],
    max_age_hours: int = 72,
    max_facts: int = 20,
) -> str:
    """Read relevant facts for given tags, deduplicate, return as markdown.

    Args:
        tags: List of scope tags to read from
        max_age_hours: Maximum age of facts to include
        max_facts: Maximum number of facts to return

    Returns:
        Markdown string ready for prompt injection, or empty string.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
    all_facts = []

    for tag in tags:
        path = SHARED_MEMORY_DIR / tag / "knowledge.jsonl"
        if not path.exists():
            continue
        size = path.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            logger.warning(
                "Shared memory for tag '%s' is %.1f MB — cleanup recommended",
                tag, size / (1024 * 1024)
            )
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry.get("timestamp", "")).timestamp()
                    if ts < cutoff:
                        continue
                    all_facts.append(entry)
                except (json.JSONDecodeError, ValueError):
                    continue

    if not all_facts:
        return ""

    deduped = deduplicate_facts(all_facts)
    recent = deduped[-max_facts:]

    parts = ["## Shared Workspace Knowledge"]
    for fact in recent:
        text = fact.get("fact", "")
        agent = fact.get("agent_id", "unknown")[:8]
        parts.append(f"- [{agent}] {text}")

    return "\n".join(parts)


def cleanup_expired_facts(max_age_days: int = 30) -> int:
    """Remove facts older than max_age_days from all knowledge.jsonl files.

    Rewrites each file in-place (read all, filter, write back).
    """
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)
    total_purged = 0

    if not SHARED_MEMORY_DIR.exists():
        return 0

    for tag_dir in SHARED_MEMORY_DIR.iterdir():
        if not tag_dir.is_dir():
            continue
        path = tag_dir / "knowledge.jsonl"
        if not path.exists():
            continue

        entries = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry.get("timestamp", "")).timestamp()
                    if ts >= cutoff:
                        entries.append(entry)
                    else:
                        total_purged += 1
                except (json.JSONDecodeError, ValueError):
                    entries.append({"fact": line, "type": "unknown"})

        with open(path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    return total_purged


def delete_agent_facts(agent_id: str) -> int:
    """Remove all facts from the shared knowledge pool that were written by a specific agent."""
    total_deleted = 0

    if not SHARED_MEMORY_DIR.exists():
        return 0

    for tag_dir in SHARED_MEMORY_DIR.iterdir():
        if not tag_dir.is_dir():
            continue
        path = tag_dir / "knowledge.jsonl"
        if not path.exists():
            continue

        entries = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("agent_id") == agent_id:
                        total_deleted += 1
                        continue
                    entries.append(entry)
                except (json.JSONDecodeError, ValueError):
                    entries.append({"fact": line, "type": "unknown"})

        with open(path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    return total_deleted
