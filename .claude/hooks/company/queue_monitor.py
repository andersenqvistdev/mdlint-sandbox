#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Forge Queue Monitor — Live view of work queue, recent completions, and escalations.

Usage:
    uv run .claude/hooks/company/queue_monitor.py              # One-shot display
    uv run .claude/hooks/company/queue_monitor.py --watch      # Live refresh (every 5s)
    uv run .claude/hooks/company/queue_monitor.py --watch 10   # Live refresh (every 10s)
    uv run .claude/hooks/company/queue_monitor.py --json       # JSON output
    uv run .claude/hooks/company/queue_monitor.py --heal       # Detect and fix queue issues
    uv run .claude/hooks/company/queue_monitor.py --heal --dry-run  # Show issues without fixing
    uv run .claude/hooks/company/queue_monitor.py --prs        # List all tasks with PRs
    uv run .claude/hooks/company/queue_monitor.py --completions 25  # Show last 25 completions
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add script directory to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from queue_io import save_queue_atomic


def find_company_dir():
    for start in [Path(__file__).resolve().parent, Path.cwd()]:
        for parent in [start] + list(start.parents):
            candidate = parent / ".company"
            if candidate.is_dir() and (candidate / "org.json").exists():
                return candidate
    return Path(".company")


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


# save_queue_atomic imported from queue_io below


def relative_time(iso_str):
    if not iso_str:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        secs = int((now - dt).total_seconds())
        if secs < 0:
            return "future"
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h {(secs % 3600) // 60}m ago"
        return f"{secs // 86400}d ago"
    except (ValueError, TypeError):
        return "?"


def trunc(s, width):
    return (s[: width - 1] + "\u2026") if len(s) > width else s


def pri_label(p):
    return {1: "P1 CRIT", 2: "P2 HIGH", 3: "P3 NORM", 4: "P4 LOW", 5: "P5 MIN"}.get(
        p, f"P{p}"
    )


def emp_short(eid, task=None):
    if not eid:
        return ""
    name = eid.replace("daemon-", "d:")
    if task and task.get("execution_mode") == "agent-team":
        size = task.get("team_size", 3)
        name = f"{name} \033[1;35m[TEAM x{size}]\033[0m"
    return name


def get_pr_status(pr_url):
    """Check PR merge status via gh CLI. Returns (is_merged, pr_number)."""
    if not pr_url:
        return None, None
    try:
        # Extract PR number from URL
        import re

        match = re.search(r"/pull/(\d+)", pr_url)
        if not match:
            return None, None
        pr_number = match.group(1)

        result = subprocess.run(
            ["gh", "pr", "view", pr_number, "--json", "state"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            import json as _json

            data = _json.loads(result.stdout)
            # state is "MERGED", "OPEN", or "CLOSED"
            return data.get("state") == "MERGED", pr_number
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None, None


def pr_status_label(pr_url, cache={}):
    """Return colored PR status label. Uses simple cache to avoid repeated gh calls."""
    if not pr_url:
        return ""
    if pr_url in cache:
        return cache[pr_url]

    is_merged, pr_num = get_pr_status(pr_url)
    if is_merged is True:
        label = f"\033[32m#PR{pr_num}\u2713\033[0m"  # Green checkmark
    elif is_merged is False:
        label = f"\033[33m#PR{pr_num}\033[0m"  # Yellow (open)
    else:
        label = "\033[2m#PR?\033[0m"  # Gray (unknown)
    cache[pr_url] = label
    return label


def get_queue_path(company_dir):
    p = company_dir / "state" / "work_queue.json"
    return p if p.exists() else company_dir / "work_queue.json"


def get_active_daemon_pids():
    pids = set()
    try:
        result = subprocess.run(
            ["pgrep", "-f", "forge_daemon"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                pids.add(line.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return pids


def _last_failure_note(health_metrics: dict) -> str:
    """Age of the newest failure, rendered next to the success rate.

    total_successes/total_failures are LIFETIME cumulative counters over
    execution ATTEMPTS (retries included) that never age out. The rate built
    from them therefore cannot recover: on 2026-08-15 the dashboard read
    69% (194/280) while every one of the 86 failures predated 2026-08-02 --
    13 days with a clean record, displayed as a two-thirds success rate.
    Read alongside autonomy_metrics (86% lifetime, 77% over 30 days, both
    over DISTINCT TASKS rather than attempts), the bare number invited the
    conclusion that something had regressed when nothing had.

    Showing when the last failure actually happened costs one field and makes
    the figure self-describing: a stale denominator is obvious at a glance.
    """
    stamp = health_metrics.get("last_failure_time")
    if not stamp:
        return ""
    try:
        when = datetime.fromisoformat(str(stamp))
    except (TypeError, ValueError):
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - when
    if delta.days >= 1:
        age = f"{delta.days}d"
    elif delta.seconds >= 3600:
        age = f"{delta.seconds // 3600}h"
    else:
        age = f"{max(delta.seconds // 60, 0)}m"
    return f" \033[2mlifetime, last fail {age} ago\033[0m"


def render_dashboard(company_dir, completions_n=10):
    lines = []
    w = 78
    queue = load_json(get_queue_path(company_dir)) or {}
    loop_data = load_json(company_dir / "state" / "loop_monitor.json")
    if not loop_data:
        loop_data = load_json(company_dir / "loop_monitor.json") or {}
    org = load_json(company_dir / "org.json") or {}
    company_name = org.get("company", {}).get("name", "Forge")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append("\033[1m" + "=" * w + "\033[0m")
    lines.append(f"\033[1m  {company_name} \u2014 QUEUE MONITOR\033[0m")
    lines.append(f"  {now_str}")
    lines.append("\033[1m" + "=" * w + "\033[0m")

    cb = loop_data.get("circuit_breaker", {})
    hm = loop_data.get("health_metrics", {})
    cb_state = cb.get("state", "unknown").upper()
    total_ok = hm.get("total_successes", 0)
    total_fail = hm.get("total_failures", 0)
    total = total_ok + total_fail
    rate = f"{total_ok / total * 100:.0f}%" if total > 0 else "n/a"
    cb_colors = {"CLOSED": "\033[32m", "OPEN": "\033[31m"}
    cb_color = cb_colors.get(cb_state, "\033[33m")
    lines.append("")
    lines.append(
        f"  Circuit: {cb_color}{cb_state}\033[0m  |  "
        f"Success: {rate} ({total_ok}/{total}){_last_failure_note(hm)}  |  "
        f"Queue: {len(queue.get('pending', []))}P / "
        f"{len(queue.get('in_progress', []))}A / "
        f"{len(queue.get('completed', []))}C"
    )
    lines.append("")

    in_progress = queue.get("in_progress", [])
    lines.append(f"\033[1;33m  IN PROGRESS ({len(in_progress)})\033[0m")
    if in_progress:
        lines.append(f"  {'Pri':<8} {'Task':<50} {'Assigned':<18}")
        lines.append(f"  {'---':<8} {'----':<50} {'--------':<18}")
        for t in in_progress:
            assigned = emp_short(t.get("assigned_to") or t.get("claimed_by", ""), t)
            lines.append(
                f"  {pri_label(t.get('priority')):<8} "
                f"{trunc(t.get('title', ''), 50):<50} "
                f"{assigned:<18} "
                f"{relative_time(t.get('claimed_at') or t.get('started_at'))}"
            )
    else:
        lines.append("  \033[2m(none)\033[0m")
    lines.append("")

    pending = queue.get("pending", [])
    lines.append(f"\033[1;36m  PENDING ({len(pending)})\033[0m")
    if pending:
        lines.append(f"  {'Pri':<8} {'Task':<50} {'Waiting':<18}")
        lines.append(f"  {'---':<8} {'----':<50} {'-------':<18}")
        for t in pending[:15]:
            lines.append(
                f"  {pri_label(t.get('priority')):<8} {trunc(t.get('title', ''), 50):<50} {relative_time(t.get('created_at'))}"
            )
            caps = ", ".join(t.get("required_capabilities", [])[:3])
            if caps:
                lines.append(f"  {'':8} \033[2m[{caps}]\033[0m")
        if len(pending) > 15:
            lines.append(f"  \033[2m... and {len(pending) - 15} more\033[0m")
    else:
        lines.append("  \033[2m(none)\033[0m")
    lines.append("")

    blocked = queue.get("blocked", [])
    if blocked:
        lines.append(f"\033[1;31m  BLOCKED ({len(blocked)})\033[0m")
        for t in blocked[:5]:
            lines.append(
                f"  {'':8} {trunc(t.get('title', ''), 50):<50} {(t.get('last_error') or 'unknown')[:40]}"
            )
        lines.append("")

    pr_open_tasks = queue.get("pr_open", [])
    if pr_open_tasks:
        lines.append(
            f"\033[1;35m  PR OPEN ({len(pr_open_tasks)}) — awaiting merge\033[0m"
        )
        lines.append(f"  {'Task':<35} {'PR':<20} {'Since':<12}")
        lines.append(f"  {'----':<35} {'--':<20} {'-----':<12}")
        for t in pr_open_tasks[:10]:
            pr_label = (
                pr_status_label(t.get("pr_url"))
                if t.get("pr_url")
                else "\033[2m-\033[0m"
            )
            lines.append(
                f"  {trunc(t.get('title', ''), 35):<35} "
                f"{pr_label:<20} "
                f"{relative_time(t.get('pr_open_at') or t.get('completed_at') or t.get('created_at'))}"
            )
        if len(pr_open_tasks) > 10:
            lines.append(f"  \033[2m... and {len(pr_open_tasks) - 10} more\033[0m")
        lines.append("")

    completed = queue.get("completed", [])
    stamped = sorted(
        [t for t in completed if t.get("completed_at")],
        key=lambda t: t.get("completed_at", ""),
        reverse=True,
    )
    unstamped = [t for t in completed if not t.get("completed_at")]
    recent = (stamped + unstamped)[:completions_n]
    lines.append(
        f"\033[1;32m  RECENT COMPLETIONS ({len(completed)} total, showing last {len(recent)})\033[0m"
    )
    if recent:
        lines.append(f"  {'When':<12} {'Task':<35} {'By':<15} {'PR':<12}")
        lines.append(f"  {'----':<12} {'----':<35} {'--':<15} {'--':<12}")
        for t in recent:
            marker = (
                "\033[32m+\033[0m"
                if t.get("result") == "completed"
                else "\033[31mx\033[0m"
            )
            completed_by = emp_short(t.get("assigned_to") or t.get("claimed_by", ""), t)
            pr_label = (
                pr_status_label(t.get("pr_url"))
                if t.get("pr_url")
                else "\033[2m-\033[0m"
            )
            lines.append(
                f"  {relative_time(t.get('completed_at')):<12} {marker} "
                f"{trunc(t.get('title', ''), 34):<34} "
                f"{trunc(completed_by, 14):<14} "
                f"{pr_label}"
            )
    else:
        lines.append("  \033[2m(none)\033[0m")
    lines.append("")

    escalations = []
    esc_dir = company_dir / "escalations"
    if esc_dir.is_dir():
        for fp in esc_dir.glob("*.json"):
            esc = load_json(fp)
            if esc and esc.get("status") != "resolved":
                escalations.append(esc)
    # Newest first BY TIME. Sorting the filenames instead ordered by prefix
    # ("task-" > "silence-" > "admission-"), which pushed whole categories to
    # the bottom regardless of age — the newest escalation sorted last and was
    # always the one the display cap dropped.
    escalations.sort(key=lambda e: str(e.get("created_at") or ""), reverse=True)
    approvals = load_json(company_dir / "pending_approvals.json")
    pending_approvals = []
    if isinstance(approvals, dict):
        pending_approvals = [
            a
            for a in approvals.get("pending", [])
            if a.get("status") in ("pending", "pending_review")
        ]
    esc_count = len(escalations) + len(pending_approvals)
    if esc_count > 0:
        lines.append(f"\033[1;31m  NEEDS ATTENTION ({esc_count})\033[0m")
        # Build task title lookup from queue for richer display
        _title_map = {}
        for _status in ("pending", "in_progress", "blocked", "completed"):
            for _t in queue.get(_status, [])[-50:]:
                _tid = _t.get("task_id", "")
                if _tid:
                    _title_map[_tid] = _t.get("title", "")
        _ESC_SHOWN = 5
        for e in escalations[:_ESC_SHOWN]:
            _eid = e.get("task_id", "?")
            # Try to get title from escalation fields, metadata, queue lookup.
            # metadata.title is what silence_sentinel and task_admission write;
            # without it every sentinel page rendered as "Unknown task".
            _meta = e.get("metadata") or {}
            _title = (
                e.get("title")
                or _meta.get("title")
                or _meta.get("task_title")
                or e.get("original_task", {}).get("title")
                or _title_map.get(_eid)
                or e.get("reason")
                or e.get("escalation_reason")
                or "Unknown task"
            )
            _trigger = e.get("trigger", e.get("escalation_trigger", ""))
            _detail = (
                f"{trunc(_title, 42)} \033[2m({_trigger})\033[0m"
                if _trigger
                else trunc(_title, 55)
            )
            lines.append(
                f"  \033[31m!\033[0m {_detail:<55} {relative_time(e.get('created_at', e.get('escalated_at')))}"
            )
        for a in pending_approvals[:_ESC_SHOWN]:
            lines.append(
                f"  \033[33m?\033[0m {trunc(a.get('title', a.get('type', '?')), 55):<55} {relative_time(a.get('submitted_at', a.get('created_at')))}"
            )
        # Say what the cap dropped. A section headed "NEEDS ATTENTION (9)" that
        # lists five reads as nine listed unless you count them.
        _hidden = max(len(escalations) - _ESC_SHOWN, 0) + max(
            len(pending_approvals) - _ESC_SHOWN, 0
        )
        if _hidden:
            lines.append(
                f"  \033[2m… and {_hidden} more — see .company/escalations/\033[0m"
            )
        lines.append("")
    else:
        lines.append("\033[1;32m  ESCALATIONS: None \u2014 all clear\033[0m")
        lines.append("")

    lines.append("\033[2m" + "-" * w + "\033[0m")
    lines.append(
        "\033[2m  P=Pending A=Active C=Completed | --watch | --json | --heal\033[0m"
    )
    lines.append("\033[2m" + "-" * w + "\033[0m")
    return "\n".join(lines)


def render_pr_list(company_dir):
    """Render table of every task carrying a pr_url, sorted newest-first."""
    queue = load_json(get_queue_path(company_dir)) or {}
    lines = []
    w = 78

    all_tasks = []
    for lane in (
        "pending",
        "in_progress",
        "blocked",
        "pr_open",
        "completed",
        "failed",
        "archived",
    ):
        for t in queue.get(lane, []):
            if t.get("pr_url"):
                all_tasks.append(t)

    all_tasks.sort(
        key=lambda t: t.get("completed_at") or t.get("created_at") or "",
        reverse=True,
    )

    lines.append("\033[1m" + "=" * w + "\033[0m")
    lines.append(f"\033[1m  ALL PRs ({len(all_tasks)})\033[0m")
    lines.append("\033[1m" + "=" * w + "\033[0m")
    lines.append("")

    if all_tasks:
        pr_cache = {}
        lines.append(f"  {'ID':<10} {'Title':<42} PR")
        lines.append(f"  {'--':<10} {'-----':<42} --")
        for t in all_tasks:
            tid = (t.get("task_id") or "?")[-8:]
            title = trunc(t.get("title", ""), 42)
            label = pr_status_label(t.get("pr_url"), cache=pr_cache)
            lines.append(f"  {tid:<10} {title:<42} {label}")
    else:
        lines.append("  \033[2m(no PRs found)\033[0m")

    lines.append("")
    lines.append("\033[2m" + "-" * w + "\033[0m")
    return "\n".join(lines)


STALE_HOURS = 2
ESC_STALE_HOURS = 48


def heal_queue(company_dir, dry_run=False):
    # P4: Run fuzzy dedup FIRST (acquires its own lock, saves independently)
    # Must run before loading queue to avoid discarding in-memory modifications
    fuzzy_findings = []
    fuzzy_actions = []
    try:
        from work_allocator import deduplicate_pending_tasks

        dedup_result = deduplicate_pending_tasks(dry_run=dry_run)
        for removed in dedup_result.get("duplicates", []):
            fuzzy_findings.append(
                {
                    "type": "fuzzy_duplicate",
                    "severity": "low",
                    "task_id": removed.get("task_id", "?"),
                    "title": removed.get("title", "")[:60],
                    "reason": f"similar to {removed.get('kept_task_id', '?')}",
                }
            )
            if not dry_run:
                fuzzy_actions.append(
                    {
                        "action": "removed_fuzzy_duplicate",
                        "task_id": removed.get("task_id"),
                    }
                )
    except Exception:
        pass  # dedup is best-effort

    queue_path = get_queue_path(company_dir)
    queue = load_json(queue_path) or {}
    now = datetime.now(timezone.utc)
    active_pids = get_active_daemon_pids()
    findings = []
    actions = []
    modified = False

    # Sweep both in_progress and blocked lanes for stranded daemon tasks.
    # blocked lane was previously only checked for tasks owned by other
    # daemons (in forge_daemon._cleanup_orphan_tasks) — but a worker can
    # die while its daemon stays alive, leaving the task stranded.
    for source in ("in_progress", "blocked"):
        for t in list(queue.get(source, [])):
            # Respect explicit human-set blocks and dependency blocks
            if source == "blocked":
                if t.get("blocked_reason") or t.get("dependencies"):
                    continue
            task_id = t.get("task_id", "?")
            claimed_by = t.get("claimed_by") or t.get("assigned_to") or ""
            claimed_at = t.get("claimed_at") or t.get("started_at")
            is_daemon = claimed_by.startswith("daemon-")
            # Extract numeric PID from 'daemon-{pid}' or 'daemon-{pid}-{ts}'.
            _cb_parts = claimed_by.split("-")
            daemon_pid = _cb_parts[1] if is_daemon and len(_cb_parts) >= 2 else ""
            pid_dead = is_daemon and daemon_pid and daemon_pid not in active_pids
            age_hours = 0.0
            if claimed_at:
                try:
                    dt = datetime.fromisoformat(claimed_at.replace("Z", "+00:00"))
                    age_hours = (now - dt).total_seconds() / 3600
                except (ValueError, TypeError):
                    pass
            if pid_dead or age_hours > STALE_HOURS:
                parts = []
                if pid_dead:
                    parts.append(f"daemon PID {daemon_pid} dead")
                if age_hours > STALE_HOURS:
                    parts.append(f"claimed {age_hours:.1f}h ago")
                findings.append(
                    {
                        "type": "stale_task",
                        "severity": "high",
                        "task_id": task_id,
                        "title": t.get("title", "")[:60],
                        "reason": f"[{source}] " + "; ".join(parts),
                    }
                )
                if not dry_run:
                    queue[source].remove(t)
                    for key in [
                        "assigned_to",
                        "assigned_at",
                        "started_at",
                        "claimed_by",
                        "claimed_at",
                    ]:
                        t[key] = None
                    queue.setdefault("pending", []).insert(0, t)
                    modified = True
                    actions.append(
                        {
                            "action": "released_stale_task",
                            "task_id": task_id,
                            "from": source,
                        }
                    )

    # Reconcile blocked tasks whose PR has already merged. When the deliverable
    # gate holds a daemon PR and a human then merges it, nothing moves the task
    # out of the blocked lane: the sweep above skips anything carrying a
    # blocked_reason (treating it as a human-set block), and the judge writes
    # exactly such a reason. The task then sits blocked forever while heal
    # reports a healthy queue. Only a MERGED PR reconciles — get_pr_status
    # returns None when the lookup fails and False for an open or
    # closed-unmerged PR, and closed-unmerged is genuinely unresolved work.
    for t in list(queue.get("blocked", [])):
        pr_url = t.get("pr_url")
        if not pr_url:
            continue
        is_merged, pr_number = get_pr_status(pr_url)
        if is_merged is not True:
            continue
        task_id = t.get("task_id", "?")
        findings.append(
            {
                "type": "merged_pr_still_blocked",
                "severity": "high",
                "task_id": task_id,
                "title": t.get("title", "")[:60],
                "reason": f"PR #{pr_number} merged but task still blocked",
            }
        )
        if not dry_run:
            queue["blocked"].remove(t)
            t["status"] = "completed"
            t["completed_at"] = now.isoformat()
            # Keep the judge's verdict for audit, but drop the active-sounding
            # field — a completed task reading as blocked is the exact
            # ambiguity this rule exists to remove.
            if t.get("blocked_reason"):
                t["previous_blocked_reason"] = t["blocked_reason"]
            t["blocked_reason"] = None
            if not isinstance(t.get("notes"), list):
                t["notes"] = []
            t["notes"].append(
                {
                    "timestamp": now.isoformat(),
                    "content": f"queue heal: reconciled after PR #{pr_number} merged",
                }
            )
            queue.setdefault("completed", []).append(t)
            modified = True
            actions.append(
                {
                    "action": "completed_merged_pr_task",
                    "task_id": task_id,
                    "pr": pr_number,
                }
            )

    seen_ids = {}
    for q_name in ["pending", "in_progress", "blocked"]:
        for t in list(queue.get(q_name, [])):
            tid = t.get("task_id")
            if not tid:
                continue
            if tid in seen_ids:
                findings.append(
                    {
                        "type": "duplicate_task",
                        "severity": "medium",
                        "task_id": tid,
                        "title": t.get("title", "")[:60],
                        "reason": f"in both {seen_ids[tid]} and {q_name}",
                    }
                )
                if not dry_run:
                    queue[q_name].remove(t)
                    modified = True
                    actions.append(
                        {"action": "removed_duplicate", "task_id": tid, "from": q_name}
                    )
            else:
                seen_ids[tid] = q_name

    for t in list(queue.get("pending", [])):
        bo = t.get("backoff_until")
        if not bo:
            continue
        try:
            if datetime.fromisoformat(bo.replace("Z", "+00:00")) < now:
                findings.append(
                    {
                        "type": "expired_backoff",
                        "severity": "low",
                        "task_id": t.get("task_id", "?"),
                        "title": t.get("title", "")[:60],
                        "reason": f"backoff expired {relative_time(bo)}",
                    }
                )
                if not dry_run:
                    t.pop("backoff_until", None)
                    modified = True
                    actions.append(
                        {"action": "cleared_backoff", "task_id": t.get("task_id")}
                    )
        except (ValueError, TypeError):
            pass

    # P2a: Stale pending detection (report-only)
    PENDING_STALE_HOURS = 72  # 3 days

    for t in queue.get("pending", []):
        created = t.get("created_at")
        if not created:
            continue
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_h = (now - dt).total_seconds() / 3600
            if age_h > PENDING_STALE_HOURS:
                findings.append(
                    {
                        "type": "stale_pending",
                        "severity": "medium",
                        "task_id": t.get("task_id", "?"),
                        "title": t.get("title", "")[:60],
                        "reason": f"pending for {age_h:.0f}h, check dependencies/routing",
                    }
                )
        except (ValueError, TypeError):
            pass

    # P2b: Archive failed tasks older than 48h
    FAILED_ARCHIVE_HOURS = 48

    for t in list(queue.get("failed", [])):
        failed_at = t.get("failed_at") or t.get("completed_at")
        if not failed_at:
            continue
        try:
            dt = datetime.fromisoformat(failed_at.replace("Z", "+00:00"))
            age_h = (now - dt).total_seconds() / 3600
            if age_h > FAILED_ARCHIVE_HOURS:
                findings.append(
                    {
                        "type": "stale_failed",
                        "severity": "low",
                        "task_id": t.get("task_id", "?"),
                        "title": t.get("title", "")[:60],
                        "reason": f"failed {age_h:.0f}h ago, archiving",
                    }
                )
                if not dry_run:
                    queue["failed"].remove(t)
                    t["archived_at"] = now.isoformat()
                    t["archive_reason"] = "stale_failed"
                    queue.setdefault("archived", []).append(t)
                    # Cap archived list to prevent unbounded growth
                    MAX_ARCHIVED = 200
                    archived = queue.get("archived", [])
                    if len(archived) > MAX_ARCHIVED:
                        queue["archived"] = archived[-MAX_ARCHIVED:]
                    modified = True
                    actions.append(
                        {"action": "archived_failed", "task_id": t.get("task_id")}
                    )
        except (ValueError, TypeError):
            pass

    # P3a: Broken dependency detection (report-only)
    failed_ids = {t.get("task_id") for t in queue.get("failed", [])}
    all_known = set()
    for qn in ["pending", "in_progress", "blocked", "completed", "failed"]:
        for t in queue.get(qn, []):
            tid = t.get("task_id")
            if tid:
                all_known.add(tid)

    for t in queue.get("pending", []):
        deps = t.get("dependencies", [])
        if not deps:
            continue
        broken = [d for d in deps if d in failed_ids]
        missing = [d for d in deps if d not in all_known]
        if broken or missing:
            findings.append(
                {
                    "type": "broken_dependency",
                    "severity": "high",
                    "task_id": t.get("task_id", "?"),
                    "title": t.get("title", "")[:60],
                    "reason": f"deps broken={broken} missing={missing}",
                }
            )

    # P3b: Backoff cap (auto-fix excessive backoff)
    MAX_BACKOFF_HOURS = 24

    for t in queue.get("pending", []):
        bo = t.get("backoff_until")
        if not bo:
            continue
        try:
            bo_dt = datetime.fromisoformat(bo.replace("Z", "+00:00"))
            remaining_h = (bo_dt - now).total_seconds() / 3600
            if remaining_h > MAX_BACKOFF_HOURS:
                findings.append(
                    {
                        "type": "excessive_backoff",
                        "severity": "medium",
                        "task_id": t.get("task_id", "?"),
                        "title": t.get("title", "")[:60],
                        "reason": f"backoff {remaining_h:.0f}h in future, capping to {MAX_BACKOFF_HOURS}h",
                    }
                )
                if not dry_run:
                    t["backoff_until"] = (
                        now + timedelta(hours=MAX_BACKOFF_HOURS)
                    ).isoformat()
                    modified = True
                    actions.append(
                        {"action": "capped_backoff", "task_id": t.get("task_id")}
                    )
        except (ValueError, TypeError):
            pass

    esc_dir = company_dir / "escalations"
    if esc_dir.is_dir():
        for fp in sorted(esc_dir.glob("*.json")):
            esc = load_json(fp)
            if not esc or esc.get("status") == "resolved":
                continue
            created = esc.get("created_at") or esc.get("escalated_at")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age_h = (now - dt).total_seconds() / 3600
                    if age_h > ESC_STALE_HOURS:
                        findings.append(
                            {
                                "type": "stale_escalation",
                                "severity": "medium",
                                "task_id": esc.get("task_id", fp.stem),
                                "title": (esc.get("title") or esc.get("reason", ""))[
                                    :60
                                ],
                                "reason": f"unresolved for {age_h:.0f}h",
                                # Detect-only, deliberately. Auto-archiving an
                                # unread page is how a same-day fix became an
                                # 11-day stall, so heal reports these and
                                # leaves them for `escalation.py resolve`.
                                "auto_fixable": False,
                                "hint": (
                                    "resolve with: escalation.py resolve "
                                    f"--task-id {esc.get('task_id', fp.stem)} "
                                    "--resolution <why>"
                                ),
                            }
                        )
                except (ValueError, TypeError):
                    pass

    pending = queue.get("pending", [])
    fixed_inv = False
    for i, t in enumerate(pending):
        if t.get("priority") == 1 and not fixed_inv:
            for j in range(i):
                if pending[j].get("priority", 5) > 1:
                    findings.append(
                        {
                            "type": "priority_inversion",
                            "severity": "low",
                            "task_id": t.get("task_id", "?"),
                            "title": t.get("title", "")[:60],
                            "reason": f"P1 behind P{pending[j].get('priority')} at pos {j}",
                        }
                    )
                    if not dry_run:
                        queue["pending"].remove(t)
                        queue["pending"].insert(0, t)
                        modified = True
                        fixed_inv = True
                        actions.append(
                            {"action": "fixed_priority", "task_id": t.get("task_id")}
                        )
                    break

    if modified and not dry_run:
        save_queue_atomic(queue, queue_path)

    # Merge P4 fuzzy dedup findings (ran at start of function)
    findings = fuzzy_findings + findings
    actions = fuzzy_actions + actions

    return {
        "timestamp": now.isoformat(),
        "dry_run": dry_run,
        "findings": findings,
        "actions": actions,
        "queue_modified": modified,
    }


def render_heal_report(result):
    lines = []
    w = 78
    findings = result.get("findings", [])
    actions = result.get("actions", [])
    # The banner reports what happened, not merely which flag was passed. It
    # used to read "HEALED" whenever dry_run was false, so a run that detected
    # findings and acted on NONE of them announced itself as a repair. That is
    # the failure shape this tool exists to catch: a control whose success
    # message is independent of whether it did anything.
    if result.get("dry_run"):
        mode = "DRY RUN"
    elif actions:
        mode = "HEALED"
    else:
        mode = "NO ACTION TAKEN"
    lines.append("\033[1m" + "=" * w + "\033[0m")
    lines.append(f"\033[1m  QUEUE HEALTH CHECK \u2014 {mode}\033[0m")
    lines.append(f"  {result.get('timestamp', '')[:19]}")
    lines.append("\033[1m" + "=" * w + "\033[0m")
    lines.append("")
    if not findings:
        lines.append("  \033[32mQueue is healthy \u2014 no issues found.\033[0m")
        lines.append("")
        return "\n".join(lines)
    sev_color = {"high": "\033[31m", "medium": "\033[33m", "low": "\033[2m"}
    sev_icon = {"high": "!!", "medium": "! ", "low": "~ "}
    by_sev = {}
    for f in findings:
        by_sev.setdefault(f.get("severity", "low"), []).append(f)
    for sev in ["high", "medium", "low"]:
        items = by_sev.get(sev, [])
        if not items:
            continue
        c = sev_color[sev]
        lines.append(f"  {c}{sev.upper()} ({len(items)})\033[0m")
        for f in items:
            lines.append(
                f"  {c}{sev_icon[sev]}\033[0m [{f.get('task_id', '?')[-8:]}] {trunc(f.get('title', ''), 45)}"
            )
            lines.append(
                f"     {c}{f['type'].replace('_', ' ')}: {f.get('reason', '')}\033[0m"
            )
        lines.append("")
    if actions:
        lines.append(f"\033[1;32m  ACTIONS TAKEN ({len(actions)})\033[0m")
        for a in actions:
            lines.append(
                f"  \033[32m+\033[0m [{a.get('task_id', '?')[-8:]}] {a.get('action', '?').replace('_', ' ')}"
            )
        lines.append("")
    if result.get("dry_run"):
        lines.append(
            f"  \033[33mDry run \u2014 {len(findings)} issues. Run --heal without --dry-run to fix.\033[0m"
        )
        lines.append("")
    else:
        # Findings heal cannot repair must be named, not omitted. Silence here
        # reads as "handled" against a HEALED banner, which is how stale
        # escalations sat unresolved for 61h while heal reported success.
        actioned = {a.get("task_id") for a in actions if a.get("task_id")}
        unfixed = [f for f in findings if f.get("task_id") not in actioned]
        if unfixed:
            lines.append(
                f"\033[1;33m  NOT AUTO-FIXED ({len(unfixed)}) \u2014 needs a human\033[0m"
            )
            for f in unfixed:
                lines.append(
                    f"  \033[33m\u2192\033[0m [{f.get('task_id', '?')[-8:]}] {f['type'].replace('_', ' ')}"
                )
            lines.append("")
    lines.append("\033[2m" + "-" * w + "\033[0m")
    return "\n".join(lines)


def render_json(company_dir):
    queue = load_json(get_queue_path(company_dir)) or {}
    completed = queue.get("completed", [])
    stamped = sorted(
        [t for t in completed if t.get("completed_at")],
        key=lambda t: t.get("completed_at", ""),
        reverse=True,
    )
    unstamped_json = [t for t in completed if not t.get("completed_at")]
    recent = (stamped + unstamped_json)[:10]
    esc_dir = company_dir / "escalations"
    esc_count = sum(
        1
        for fp in (esc_dir.glob("*.json") if esc_dir.is_dir() else [])
        if (load_json(fp) or {}).get("status") != "resolved"
    )
    return json.dumps(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pending": len(queue.get("pending", [])),
            "in_progress": len(queue.get("in_progress", [])),
            "completed_total": len(completed),
            "blocked": len(queue.get("blocked", [])),
            "in_progress_tasks": [
                {
                    "task_id": t.get("task_id"),
                    "title": t.get("title"),
                    "priority": t.get("priority"),
                    "assigned_to": t.get("assigned_to"),
                }
                for t in queue.get("in_progress", [])
            ],
            "pending_tasks": [
                {
                    "task_id": t.get("task_id"),
                    "title": t.get("title"),
                    "priority": t.get("priority"),
                }
                for t in queue.get("pending", [])
            ],
            "recent_completions": [
                {
                    "task_id": t.get("task_id"),
                    "title": t.get("title"),
                    "completed_at": t.get("completed_at"),
                    "assigned_to": t.get("assigned_to"),
                }
                for t in recent
            ],
            "escalations": esc_count,
        },
        indent=2,
    )


def main():
    args = sys.argv[1:]

    if "-h" in args or "--help" in args:
        print(__doc__.strip())
        sys.exit(0)

    known_flags = {
        "--json",
        "--heal",
        "--dry-run",
        "--watch",
        "--prs",
        "--completions",
        "-h",
        "--help",
    }
    for a in args:
        if a.startswith("-") and a not in known_flags:
            print(f"Unknown option: {a}", file=sys.stderr)
            print(__doc__.strip(), file=sys.stderr)
            sys.exit(2)

    company_dir = find_company_dir()

    completions_n = 10
    if "--completions" in args:
        idx = args.index("--completions")
        if idx + 1 < len(args):
            try:
                completions_n = int(args[idx + 1])
            except ValueError:
                pass

    if "--prs" in args:
        print(render_pr_list(company_dir))
    elif "--json" in args:
        print(render_json(company_dir))
    elif "--heal" in args:
        result = heal_queue(company_dir, dry_run="--dry-run" in args)
        print(render_heal_report(result))
        if not sys.stdout.isatty():
            print(json.dumps(result, indent=2))
        sys.exit(0 if not result["findings"] else 1)
    elif "--watch" in args:
        interval = 5
        for i, a in enumerate(args):
            if a == "--watch" and i + 1 < len(args):
                try:
                    interval = int(args[i + 1])
                except ValueError:
                    pass
        try:
            while True:
                os.system("clear")
                print(render_dashboard(company_dir, completions_n=completions_n))
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        print(render_dashboard(company_dir, completions_n=completions_n))


if __name__ == "__main__":
    main()
