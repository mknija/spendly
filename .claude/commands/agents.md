---
description: Create or update a Claude Code subagent (replacement for the removed /agents wizard)
argument-hint: "[what the subagent should do, e.g. a code-reviewer subagent that checks for SQL injection]"
allowed-tools: Skill, AskUserQuestion, Read, Glob
---

You are helping the user create or update a Claude Code subagent definition
for this project.

User input: $ARGUMENTS

## Step 1 — Check existing subagents

List `.claude/agents/*.md` (project-level) so you know what already exists
and can tell a "create new" request from an "update existing" one.

## Step 2 — Determine intent

If `$ARGUMENTS` is empty, ask the user (via AskUserQuestion) two things:

1. Create a new subagent, or update an existing one (show existing names
   from Step 1 as options if any exist)
2. What the subagent should do — its purpose/task, when it should be used,
   and, if known, which tools it needs

If `$ARGUMENTS` is not empty, treat it as the description of the subagent
to create or update. Only ask follow-up questions if the request is too
ambiguous to act on (e.g. missing a clear purpose).

## Step 3 — Invoke the create-agent skill

Call the `create-agent` skill with the user's description, passing through
whether this is a new agent or an update to an existing one. Let that skill
handle picking the name, description, system prompt, tool access, and model,
and writing the result to `.claude/agents/<name>.md`.

## Step 4 — Report

Print a short summary:
```
Agent:  <name>
File:   .claude/agents/<name>.md
Use:    <one-line description of when it triggers>
```
