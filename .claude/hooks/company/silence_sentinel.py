#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Silence sentinel — makes the daemon's silence observable (plan item 4, 2026-07-26).

The failure mode this closes: the scout was dead for two nights, the queue sat
empty for hours, and the WS-119 watchdog self-killed nine times in a week —
and none of it surfaced until a human went looking. Autonomy that fails
silently is indistinguishable from autonomy that is working; this module makes
the difference visible.

Four silence conditions, each raised as an escalation record (surfaced by
/pending and /respond, and by the opt-in notifications.escalation channels in
forge-config.json — enable osascript there to get an actual desktop page):

1. scout_silent      — newest scout/* PR is older than scout_silent_hours.
                       The message carries the backpressure caveat: a quiet
                       night can mean the intake is saturated, not broken
                       (scout rule 8) — the alert says "look", not "panic".
2. queue_empty       — pending lane continuously empty longer than
                       queue_empty_hours while the daemon is running.
3. daemon_restarts   — restarts_per_day_threshold+ daemon restarts within
                       24h, detected via daemon.pid started_at changes. The
                       WS-119 watchdog SIGKILLs the process, which by design
                       cannot record its own death — watching the pid
                       snapshot catches every restart cause generically.
4. brief_skips       — a goal held back by the autofill brief-quality gate
                       for longer than brief_skip_persist_hours (its assessor
                       needs the PR #301 evidence treatment).

Alerts dedup per condition key per escalation_dedup_hours. Every check fails
open: a gh timeout or unreadable state file must never fabricate an alert
(2026-07-25: fifteen gh timeouts made the metrics lie; alerting must not
repeat that) — and must never break the daemon loop.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Bounded tail scan of autofill_brief_skips.jsonl (append-only, chronological).
_SKIP_LOG_MAX_LINES = 500

# Bounded restart-event history kept in sentinel state.
_MAX_RESTART_EVENTS = 50


@dataclass
class SentinelConfig:
    """All paths anchor on base_dir (the project root) so test isolation is a
    single base_dir=tmp_path override — never cwd-relative defaults."""

    base_dir: Path
    scout_silent_hours: float = 48.0
    queue_empty_hours: float = 4.0
    restarts_per_day_threshold: int = 3
    brief_skip_persist_hours: float = 24.0
    scout_check_min_interval_hours: float = 6.0
    escalation_dedup_hours: float = 24.0
    scout_enabled: bool = True
    git_update_blocked_hours: float = 1.0
    git_update_blocked_min_failures: int = 3

    @property
    def company_dir(self) -> Path:
        return self.base_dir / ".company"

    @property
    def state_path(self) -> Path:
        return self.company_dir / "state" / "silence_sentinel.json"

    @property
    def queue_path(self) -> Path:
        return self.company_dir / "state" / "work_queue.json"

    @property
    def pid_path(self) -> Path:
        return self.company_dir / "daemon.pid"

    @property
    def skips_path(self) -> Path:
        return self.company_dir / "state" / "autofill_brief_skips.jsonl"

    @property
    def git_update_failures_path(self) -> Path:
        return self.company_dir / "state" / "git_update_failures.json"

    @property
    def escalations_dir(self) -> Path:
        return self.company_dir / "escalations"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def _load_state(config: SentinelConfig) -> dict:
    try:
        data = json.loads(config.state_path.read_text())
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError, FileNotFoundError):
        pass
    return {}


def _save_state(config: SentinelConfig, state: dict) -> None:
    """Atomic write (mkstemp + replace) — a torn state file must never make
    the next cycle double-alert or lose the empty-since anchor."""
    path = config.state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(state, handle, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _parse_ts(value: Any) -> datetime | None:
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Checks — each returns a finding dict or None, and only mutates its own
# state keys. All fail open.
# ---------------------------------------------------------------------------


def _default_gh_runner(args: list[str]) -> str | None:
    """Run gh, return stdout or None on any failure (fail-open)."""
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def check_scout_silence(
    config: SentinelConfig,
    state: dict,
    now: datetime,
    run_gh: Callable[[list[str]], str | None],
) -> dict | None:
    """Newest scout/* PR older than the threshold -> finding.

    Rate-limited to one gh call per scout_check_min_interval_hours. A gh
    failure records nothing and alerts nothing — a flaky gh must never
    fabricate a dead scout (the 07-25 instrument-lie lesson).
    """
    if not config.scout_enabled:
        return None
    last_check = _parse_ts(state.get("last_scout_check"))
    if (
        last_check
        and (now - last_check).total_seconds()
        < config.scout_check_min_interval_hours * 3600
    ):
        newest = _parse_ts(state.get("last_scout_pr_at"))
    else:
        output = run_gh(
            [
                "pr",
                "list",
                "--search",
                "head:scout/",
                "--state",
                "all",
                "--limit",
                "1",
                "--json",
                "createdAt",
            ]
        )
        if output is None:
            return None
        try:
            rows = json.loads(output or "[]")
        except json.JSONDecodeError:
            return None
        state["last_scout_check"] = now.isoformat()
        newest = _parse_ts(rows[0].get("createdAt")) if rows else None
        if newest:
            state["last_scout_pr_at"] = newest.isoformat()

    if newest is None:
        # No scout PR has ever been observed — that is its own kind of
        # silence, but only alert once a check has actually succeeded.
        if not state.get("last_scout_check"):
            return None
        age_hours = float("inf")
    else:
        age_hours = (now - newest).total_seconds() / 3600

    if age_hours <= config.scout_silent_hours:
        return None
    age_text = "never" if age_hours == float("inf") else f"{age_hours:.0f}h ago"
    return {
        "condition": "scout_silent",
        "title": f"Scout silent: newest scout/* PR is {age_text}",
        "details": {
            "last_scout_pr_at": state.get("last_scout_pr_at"),
            "threshold_hours": config.scout_silent_hours,
            "note": (
                "A quiet night can mean intake is saturated, not broken "
                "(scout backpressure rule 8). Check "
                "state/task_admission_rejections.jsonl and the scout "
                "LaunchAgent before assuming failure."
            ),
        },
    }


def check_queue_empty(
    config: SentinelConfig, state: dict, now: datetime
) -> dict | None:
    """Pending lane continuously empty longer than the threshold -> finding."""
    try:
        queue = json.loads(config.queue_path.read_text())
        pending = len(queue.get("pending", []))
    except (OSError, json.JSONDecodeError, FileNotFoundError):
        return None

    if pending > 0:
        state.pop("queue_empty_since", None)
        return None

    since = _parse_ts(state.get("queue_empty_since"))
    if since is None:
        state["queue_empty_since"] = now.isoformat()
        return None

    empty_hours = (now - since).total_seconds() / 3600
    if empty_hours <= config.queue_empty_hours:
        return None
    return {
        "condition": "queue_empty",
        "title": f"Work queue empty for {empty_hours:.1f}h",
        "details": {
            "empty_since": state.get("queue_empty_since"),
            "threshold_hours": config.queue_empty_hours,
            "note": (
                "Autofill may be quality-skipping every goal (see "
                "state/autofill_brief_skips.jsonl) or all sources may be "
                "idle. An empty queue is cheaper than vague tasks, but "
                "hours of it deserves a look."
            ),
        },
    }


def check_daemon_restarts(
    config: SentinelConfig, state: dict, now: datetime
) -> dict | None:
    """Threshold+ restarts within 24h -> finding.

    Detects restarts by watching daemon.pid started_at change between
    sentinel cycles — catches WS-119 self-SIGKILLs, crashes, and launchd
    respawns alike, none of which can reliably record their own death.
    """
    try:
        pid_data = json.loads(config.pid_path.read_text())
        started_at = str(pid_data.get("started_at", ""))
    except (OSError, json.JSONDecodeError, FileNotFoundError):
        return None
    if not started_at:
        return None

    events = [e for e in state.get("restart_events", []) if isinstance(e, str)]
    previous = state.get("last_daemon_started_at")
    if previous and previous != started_at:
        events.append(now.isoformat())
        events = events[-_MAX_RESTART_EVENTS:]
        state["restart_events"] = events
    state["last_daemon_started_at"] = started_at

    recent = [
        ts
        for e in events
        if (ts := _parse_ts(e)) and (now - ts).total_seconds() < 24 * 3600
    ]
    if len(recent) < config.restarts_per_day_threshold:
        return None
    return {
        "condition": "daemon_restarts",
        "title": f"Daemon restarted {len(recent)}x in 24h",
        "details": {
            "restarts_24h": len(recent),
            "threshold": config.restarts_per_day_threshold,
            "note": (
                "Repeated restarts usually mean the WS-119 heartbeat "
                "watchdog is self-killing a hung loop — check "
                ".company/logs for 'watchdog: heartbeat stale' lines."
            ),
        },
    }


def check_brief_skips(
    config: SentinelConfig, state: dict, now: datetime
) -> dict | None:
    """A goal quality-skipped for longer than the persistence window -> finding.

    One skip record is the gate doing its job; the same goal skipped across
    brief_skip_persist_hours means its assessor never emits evidence and
    needs the PR #301 treatment — that is a human/interactive task.
    """
    try:
        lines = config.skips_path.read_text().splitlines()
    except (OSError, FileNotFoundError):
        return None

    per_goal: dict[str, list[datetime]] = {}
    for line in lines[-_SKIP_LOG_MAX_LINES:]:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _parse_ts(record.get("ts"))
        goal_id = record.get("goal_id")
        if ts and goal_id:
            per_goal.setdefault(str(goal_id), []).append(ts)

    persistent: list[str] = []
    recent_window = 24 * 3600
    for goal_id, stamps in sorted(per_goal.items()):
        newest = max(stamps)
        oldest = min(stamps)
        if (now - newest).total_seconds() > recent_window:
            continue  # not currently skipping
        if (newest - oldest).total_seconds() / 3600 >= config.brief_skip_persist_hours:
            persistent.append(goal_id)

    if not persistent:
        return None
    return {
        "condition": "brief_skips",
        "title": (
            f"Autofill quality gate held {', '.join(persistent)} for "
            f">{config.brief_skip_persist_hours:.0f}h"
        ),
        "details": {
            "goals": persistent,
            "note": (
                "These goals' assessors emit actions without verified "
                "pointers or measured evidence. Upgrade them with the "
                "PR #301 pattern (name the failing artifacts) or mark "
                "actions [INFRA-ONLY]/[OWNER-ONLY]."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Alerting
# ---------------------------------------------------------------------------


def check_git_update_blocked(
    config: SentinelConfig, state: dict, now: datetime
) -> dict | None:
    """The daemon has been failing to fetch/pull origin/main for hours -> finding.

    The daemon records every consecutive failure in
    state/git_update_failures.json (forge_daemon._record_git_update_failure)
    and deletes the file on the next successful pull. 314 consecutive
    failures — a stale .git/index.lock, 2026-08-20 → 08-28 — produced only
    WARNING lines while the checkout froze and every worktree shipped
    against a stale base.
    """
    try:
        data = json.loads(config.git_update_failures_path.read_text())
    except (OSError, json.JSONDecodeError, FileNotFoundError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        consecutive = int(data.get("consecutive", 0) or 0)
    except (TypeError, ValueError):
        return None
    first = _parse_ts(data.get("first_failed_at"))
    if first is None or consecutive < config.git_update_blocked_min_failures:
        return None
    blocked_hours = (now - first).total_seconds() / 3600
    if blocked_hours <= config.git_update_blocked_hours:
        return None
    stage = data.get("stage") or "pull"
    return {
        "condition": "git_update_blocked",
        "title": (
            f"Git updates failing for {blocked_hours:.1f}h "
            f"({consecutive} consecutive {stage} failures)"
        ),
        "details": {
            "first_failed_at": data.get("first_failed_at"),
            "last_failed_at": data.get("last_failed_at"),
            "consecutive": consecutive,
            "stage": stage,
            "last_error": data.get("last_error"),
            "note": (
                "The daemon is running stale code and, wherever a worktree "
                "falls back to local main, shipping against a stale base. "
                "Usual causes: a .git/index.lock the policy will not remove "
                "(non-empty and under an hour old), a permanent local "
                "override that origin/main also changed, or an unreachable "
                "remote. Fix the cause; the file clears on the next "
                "successful pull."
            ),
        },
    }


def _raise_alert(
    config: SentinelConfig, state: dict, finding: dict, now: datetime
) -> bool:
    """Write an escalation record and fire opt-in notifications.

    Deduped per condition per escalation_dedup_hours. Returns True when an
    alert was actually raised. Notification failures never affect the record.
    """
    condition = finding["condition"]
    last_alerts = state.setdefault("last_alerts", {})
    previous = _parse_ts(last_alerts.get(condition))
    if (
        previous
        and (now - previous).total_seconds() < config.escalation_dedup_hours * 3600
    ):
        return False

    record_id = f"silence-{condition}-{now.strftime('%Y%m%d%H%M')}"
    record = {
        "task_id": record_id,
        "current_tier": 2,
        "status": "pending",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "original_agent": "silence_sentinel",
        "current_agent": None,
        "trigger": "silence_sentinel",
        "trigger_details": finding.get("details", {}),
        "events": [
            {
                "timestamp": now.isoformat(),
                "tier": 2,
                "trigger": condition,
                "action_taken": finding["title"],
                "resolved": False,
            }
        ],
        "metadata": {"title": finding["title"], "condition": condition},
    }
    try:
        config.escalations_dir.mkdir(parents=True, exist_ok=True)
        (config.escalations_dir / f"{record_id}.json").write_text(
            json.dumps(record, indent=2)
        )
    except OSError:
        return False

    last_alerts[condition] = now.isoformat()

    # Opt-in page (osascript / webhook) — best-effort, never fatal.
    try:
        try:
            from . import escalation as escalation_mod  # type: ignore[attr-defined]
        except ImportError:
            import escalation as escalation_mod  # type: ignore[no-redef]

        escalation_record = escalation_mod.EscalationRecord(
            task_id=record_id,
            current_tier=2,
            status="pending",
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            trigger="silence_sentinel",
            trigger_details=finding.get("details", {}),
        )
        escalation_mod.fire_escalation_opt_in_notifications(
            escalation_record, finding["title"]
        )
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# Cycle
# ---------------------------------------------------------------------------


def run_sentinel_cycle(
    config: SentinelConfig,
    *,
    now: datetime | None = None,
    run_gh: Callable[[list[str]], str | None] | None = None,
) -> dict:
    """Run all silence checks; raise deduped alerts; persist state.

    Returns {"findings": [...], "alerts_raised": [...]} — findings lists every
    currently-true condition, alerts_raised only those that were newly paged
    this cycle (the rest were within the dedup window).
    """
    now = now or datetime.now(timezone.utc)
    run_gh = run_gh or _default_gh_runner
    state = _load_state(config)

    findings: list[dict] = []
    for check in (
        lambda: check_scout_silence(config, state, now, run_gh),
        lambda: check_queue_empty(config, state, now),
        lambda: check_daemon_restarts(config, state, now),
        lambda: check_brief_skips(config, state, now),
        lambda: check_git_update_blocked(config, state, now),
    ):
        try:
            finding = check()
        except Exception:
            finding = None  # a broken check must never break the cycle
        if finding:
            findings.append(finding)

    alerts_raised = [
        f["condition"] for f in findings if _raise_alert(config, state, f, now)
    ]

    try:
        _save_state(config, state)
    except Exception:
        pass

    return {"findings": findings, "alerts_raised": alerts_raised}
