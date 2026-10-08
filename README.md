# herdr-claude-title

A tiny [herdr](https://herdr.dev) plugin that names a tab after its Claude
Code session title — nothing else. No directory, no git branch, no agent
name, just the title.

## How it works

Every 2 seconds it polls `herdr api snapshot` (via the `herdr` CLI) for panes
running a Claude Code session, then resolves a title for each one in this
order:

1. **A manual `/rename`** — Claude Code writes this to
   `~/.claude/sessions/<pid>.json` as `"name"` with `"nameSource":"user"`.
   An explicit rename always wins.
2. **Claude's own AI-generated title** — a one-time summary of your first
   prompt, written into the session's transcript
   (`~/.claude/projects/.../<session-id>.jsonl`) as a line with
   `"type":"ai-title"` and an `"aiTitle"` field.

`nameSource` values other than `"user"` (`"derived"`, `"collision"`) are a
guess from the working directory, not a real title, so they're ignored.

When a title is found, it calls `herdr tab rename <tab_id> "<title>"`. Tabs
with no resolvable Claude session are left alone.

## Requirements

- Python 3
- `herdr` on `PATH` (the plugin shells out to it rather than talking to the
  socket directly)

## Install

```bash
git clone https://github.com/<you>/herdr-claude-title.git
cd herdr-claude-title
herdr plugin link .
```

`herdr plugin link` enables it by default. Check with:

```bash
herdr plugin list
```

## Updating after a code change

There's no `restart` action wired up, so cycle it by hand:

```bash
herdr plugin disable claude-title
herdr plugin enable claude-title
```

## Why

The full-featured [herdr-auto-title](https://github.com/kryptamine/herdr-auto-title)
plugin composes a richer title (`context › branch › agent › activity`).
This one deliberately does less: just the Claude session's own title, for
anyone who wants that and nothing more.
