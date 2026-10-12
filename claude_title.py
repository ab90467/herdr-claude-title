#!/usr/bin/env python3
"""Names each tab after its Claude Code session title, nothing else.

Polls the herdr socket through the herdr CLI, finds panes running a Claude
Code session, reads that session's own transcript for the AI-generated
title, and renames the tab to just that — no directory, no branch, no
agent name.
"""

import glob
import json
import os
import re
import subprocess
import sys
import time

POLL_SECONDS = 2
MAX_TITLE_LENGTH = 60
EMOJI_PREFIX = "🤖 "

SESSION_ID_RE = re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
CLAUDE_HOME = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def herdr(*args):
    out = subprocess.run(
        ["herdr", *args], capture_output=True, text=True, check=True
    ).stdout
    payload = json.loads(out)
    if "error" in payload:
        raise RuntimeError(f"herdr {' '.join(args)}: {payload['error']}")
    return payload["result"]


def slug(path):
    """Claude Code's own rule: every non-alphanumeric character becomes a dash."""
    return re.sub(r"[^a-zA-Z0-9]", "-", path)


def find_transcript(session_id, cwd):
    name = session_id + ".jsonl"

    if cwd:
        candidate = os.path.join(CLAUDE_HOME, "projects", slug(cwd), name)
        if os.path.isfile(candidate):
            return candidate

    matches = glob.glob(os.path.join(CLAUDE_HOME, "projects", "*", name))
    return matches[0] if matches else None


def ai_title(path):
    title = None
    try:
        with open(path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") == "ai-title" and entry.get("aiTitle"):
                    title = entry["aiTitle"]
    except OSError:
        return None

    return title


def user_renamed_title(session_id):
    """A /rename lands in ~/.claude/sessions/<pid>.json, not the transcript:
    "nameSource":"user" is an explicit rename, as against "derived"/"collision",
    which are just a guess from the directory and not a title worth showing.
    """
    for path in glob.glob(os.path.join(CLAUDE_HOME, "sessions", "*.json")):
        try:
            with open(path, "r", errors="ignore") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        if data.get("sessionId") == session_id and data.get("nameSource") == "user":
            return data.get("name")

    return None


def sanitize(title):
    title = " ".join(title.split())
    return title[:MAX_TITLE_LENGTH]


def main():
    last = {}
    seen = set()
    warned_empty = False

    print("claude-title: watching for Claude Code sessions", flush=True)

    while True:
        try:
            snapshot = herdr("api", "snapshot")["snapshot"]
            claude_panes = 0

            for pane in snapshot["panes"]:
                session = pane.get("agent_session")
                if not session or session.get("agent") != "claude":
                    continue
                if session.get("kind") != "id":
                    continue

                claude_panes += 1
                session_id = session["value"]
                if not SESSION_ID_RE.match(session_id):
                    continue

                title = user_renamed_title(session_id)

                if not title:
                    path = find_transcript(session_id, pane.get("cwd"))
                    if not path:
                        if session_id not in seen:
                            print(
                                f"claude-title: no transcript found for session "
                                f"{session_id} (cwd={pane.get('cwd')!r})",
                                flush=True,
                            )
                            seen.add(session_id)
                        continue

                    title = ai_title(path)
                    if not title:
                        if session_id not in seen:
                            print(
                                f"claude-title: transcript found but no title yet "
                                f"for session {session_id} ({path})",
                                flush=True,
                            )
                            seen.add(session_id)
                        continue

                seen.add(session_id)
                title = sanitize(title)
                tab_id = pane["tab_id"]
                if last.get(tab_id) == title:
                    continue

                display_title = EMOJI_PREFIX + title
                herdr("tab", "rename", tab_id, display_title)
                print(f"claude-title: renamed tab {tab_id} -> {display_title!r}", flush=True)
                last[tab_id] = title

            if claude_panes == 0:
                if not warned_empty:
                    print("claude-title: no Claude Code panes found", flush=True)
                    warned_empty = True
            else:
                warned_empty = False
        except Exception as exc:
            print(f"claude-title: {exc}", file=sys.stderr, flush=True)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
