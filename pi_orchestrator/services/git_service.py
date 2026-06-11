"""
Git service for Slice of Pi — manage agent git repositories.

Each agent's repo lives at ~/.pi/agent/repos/<agent_name>/.
Supports init, status, commit, push, pull, log, and diff operations.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from ..config import PI_AGENT_DIR

logger = logging.getLogger(__name__)

REPOS_DIR = PI_AGENT_DIR / "repos"


def _repo_path(agent_name: str) -> Path:
    return REPOS_DIR / agent_name


async def _run_git(
    agent_name: str,
    *args: str,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """Run a git command in the agent's repo directory."""
    repo = _repo_path(agent_name)
    if not repo.exists():
        return (1, "", f"Repository not found at {repo}")

    cmd = ("git",) + args
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(repo),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        return (proc.returncode or 0, out, err)
    except asyncio.TimeoutError:
        return (1, "", f"Git command timed out: {' '.join(cmd)}")
    except FileNotFoundError:
        return (1, "", "git binary not found on system")
    except Exception as e:
        return (1, "", str(e))


# ── Status ─────────────────────────────────────────────────────────


async def status(agent_name: str) -> dict:
    """Return parsed git status for an agent's repo."""
    code, out, err = await _run_git(agent_name, "status", "--porcelain=v1", "-b")
    if code != 0:
        return {"enabled": False, "error": err or "Unknown error"}

    lines = out.split("\n") if out else []
    branch = ""
    ahead = 0
    behind = 0
    modified: list[str] = []
    staged: list[str] = []
    untracked: list[str] = []

    for line in lines:
        if line.startswith("## "):
            # Branch line: "## main...origin/main [ahead 1, behind 2]"
            branch_part = line[3:]
            if "..." in branch_part:
                branch = branch_part.split("...")[0]
                # Parse ahead/behind
                if "[" in branch_part:
                    status_info = branch_part[branch_part.index("["):]
                    if "ahead" in status_info:
                        ahead = int(status_info.split("ahead")[1].split()[0])
                    if "behind" in status_info:
                        behind = int(status_info.split("behind")[1].split().rstrip("]"))
            else:
                branch = branch_part
        elif len(line) > 2:
            status_code = line[:2]
            filepath = line[3:]
            if status_code == "?? ":
                untracked.append(filepath)
            elif status_code[0] != " ":
                staged.append(filepath)
            else:
                modified.append(filepath)

    # Get current branch name
    if not branch:
        code2, branch, _ = await _run_git(agent_name, "rev-parse", "--abbrev-ref", "HEAD")
        if code2 != 0:
            branch = "unknown"

    # Count commits ahead/behind
    if not ahead and not behind:
        code3, out3, _ = await _run_git(agent_name, "rev-list", "--left-right", "--count", "HEAD...@{u}", timeout=10)
        if code3 == 0 and out3:
            parts = out3.split()
            if len(parts) == 2:
                behind = int(parts[0]) if parts[0].isdigit() else 0
                ahead = int(parts[1]) if parts[1].isdigit() else 0

    return {
        "enabled": True,
        "branch": branch,
        "ahead": ahead,
        "behind": behind,
        "modified": modified,
        "staged": staged,
        "untracked": untracked,
        "has_remote": await _has_remote(agent_name),
    }


async def _has_remote(agent_name: str) -> bool:
    code, out, _ = await _run_git(agent_name, "remote", "-v")
    return code == 0 and bool(out.strip())


# ── Log ────────────────────────────────────────────────────────────


async def log(agent_name: str, limit: int = 20) -> list[dict]:
    """Return recent commit history."""
    code, out, err = await _run_git(
        agent_name, "log", f"--max-count={limit}",
        "--format=%H|||%an|||%ae|||%ai|||%s",
    )
    if code != 0:
        return [{"error": err or "No commits yet"}]

    commits = []
    for line in out.split("\n") if out else []:
        parts = line.split("|||")
        if len(parts) >= 5:
            commits.append({
                "hash": parts[0][:7],
                "full_hash": parts[0],
                "author": parts[1],
                "email": parts[2],
                "date": parts[3],
                "message": "|||".join(parts[4:]),
            })
    return commits


# ── Diff ───────────────────────────────────────────────────────────


async def diff(agent_name: str, hash: str) -> dict:
    """Return diff for a specific commit."""
    code, out, err = await _run_git(agent_name, "show", hash, "--stat", "--format=%H|||%an|||%s|||%ai")
    if code != 0:
        return {"error": err or "Commit not found"}

    lines = out.split("\n") if out else []
    meta = {}
    stat_lines = []

    for i, line in enumerate(lines):
        if "|||" in line:
            parts = line.split("|||")
            meta = {
                "hash": parts[0][:7],
                "author": parts[1] if len(parts) > 1 else "",
                "message": parts[2] if len(parts) > 2 else "",
                "date": parts[3] if len(parts) > 3 else "",
            }
        elif line.strip():
            stat_lines.append(line)

    # Get full diff
    code2, diff_out, _ = await _run_git(agent_name, "diff", f"{hash}~1..{hash}", timeout=15)
    if code2 != 0:
        # Maybe it's the first commit
        code2, diff_out, _ = await _run_git(agent_name, "show", hash, "--format=", timeout=15)
    if code2 != 0:
        diff_out = ""

    return {
        "meta": meta,
        "stat": stat_lines,
        "diff": diff_out,
    }


# ── Init ───────────────────────────────────────────────────────────


async def init_repo(agent_name: str, repo_url: Optional[str] = None) -> dict:
    """Initialize a git repo for an agent. Optionally set up a remote."""
    repo = _repo_path(agent_name)
    repo.mkdir(parents=True, exist_ok=True)

    # Check if already a repo
    git_dir = repo / ".git"
    if git_dir.exists():
        return {"status": "exists", "path": str(repo)}

    # git init
    code, out, err = await _run_git(agent_name, "init")
    if code != 0:
        return {"status": "error", "error": err or "Init failed"}

    # Create .gitignore
    gitignore = repo / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# Agent files\n*.log\n*.jsonl\n.env\nnode_modules/\n"
        )

    # git add -A + initial commit
    await _run_git(agent_name, "add", "-A")
    await _run_git(agent_name, "commit", "-m", "Initial commit")

    # Set up remote if provided
    if repo_url:
        rc, ro, re = await _run_git(agent_name, "remote", "add", "origin", repo_url)
        if rc != 0:
            return {"status": "init_no_remote", "error": re, "path": str(repo)}

        # Check if default branch is main or master
        code_b, branch, _ = await _run_git(agent_name, "rev-parse", "--abbrev-ref", "HEAD")
        branch_name = branch.strip() if code_b == 0 else "main"

        # Push
        rc2, _, re2 = await _run_git(agent_name, "push", "-u", "origin", branch_name, timeout=60)
        if rc2 != 0:
            return {"status": "init_push_failed", "error": re2, "path": str(repo)}
        return {"status": "initialized", "path": str(repo), "remote": repo_url}

    return {"status": "initialized", "path": str(repo)}


# ── Commit ─────────────────────────────────────────────────────────


async def commit(agent_name: str, message: str) -> dict:
    """Stage all changes and commit."""
    code, out, err = await _run_git(agent_name, "add", "-A")
    if code != 0:
        return {"status": "error", "error": err or "Stage failed"}

    code, out, err = await _run_git(agent_name, "commit", "-m", message)
    if code != 0:
        return {"status": "error", "error": err or "Commit failed"}
    return {"status": "committed", "hash": out.split()[0] if out else ""}


# ── Push ───────────────────────────────────────────────────────────


async def push(agent_name: str) -> dict:
    """Push to remote."""
    code, out, err = await _run_git(agent_name, "push", timeout=60)
    if code != 0:
        return {"status": "error", "error": err or "Push failed"}
    return {"status": "pushed"}


# ── Pull ───────────────────────────────────────────────────────────


async def pull(agent_name: str) -> dict:
    """Pull from remote."""
    code, out, err = await _run_git(agent_name, "pull", timeout=60)
    if code != 0:
        return {"status": "error", "error": err or "Pull failed"}
    return {"status": "pulled"}
