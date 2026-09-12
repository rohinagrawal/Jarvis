# Agent Assets Bootstrap

Use this skill when creating, importing, or refreshing a shared `.agents/` setup in a repository — for any language or stack, with no other repo required as a source.

## Goal

Create a lightweight, repo-specific agent setup that works with any LLM surface that reads `AGENTS.md`, `.agents/README.md`, or tool-specific adapters. Every file this skill produces is generated inline from the templates below — never copied from another project.

## Step 0: Gather Inputs

Determine, from the repo or by asking the user (do not guess silently on anything load-bearing):

- **Project name** — repo directory name, or the `name` field in `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod`, etc.
- **One-line project summary** — what the repo is / its stack, for the README's "Project Context" section. Keep it short and factual (e.g. "a Go CLI for X", "a Python package managed with uv").
- **Which tool adapters are needed** — ask the user which of Codex, Cursor, or others they use. Claude needs no adapter (it reads skills/AGENTS.md natively). Don't create adapter files for tools the user doesn't use.
- **Whether an env template is needed** — only add `.agents/.env.example` if the project's agent workflows plausibly need local secrets or tokens (e.g. an MCP server). Skip it otherwise; it's not part of the default set.

## Step 1: Create Directories

```bash
mkdir -p .agents/rules .agents/scripts .agents/skills/agents-bootstrap .agents/workspace
```

Add `.agents/mcp/` only when the project actually needs a shared MCP server or local tool surface — omit it by default.

## Step 2: Write the Files

Generate each file below verbatim, substituting `{{PROJECT_NAME}}` and `{{PROJECT_SUMMARY}}` with the Step 0 answers. These templates are the entire source of truth — no other repo's `.agents/` folder is required to produce them.

### `AGENTS.md` (repo root)

```markdown
# AGENTS.md

## Project

{{PROJECT_SUMMARY}}

Shared agent assets live under `.agents/`.

Repo-wide agent instructions live in `.agents/README.md`.

Use `.agents/README.md` as the source of truth for shared skills, rules, manifest conventions, and validation.
```

### `.agents/README.md`

```markdown
# {{PROJECT_NAME}} Agent Guide

This repository keeps shared agent assets under `.agents/`.

The repo root `AGENTS.md` stays a thin compatibility file that points at this guide so tools that look for `AGENTS.md` get the same source of truth.

## Project Context

{{PROJECT_SUMMARY}}

## Directory Layout

\```
.agents/
├── README.md              # Shared agent guide
├── manifest.json          # Shared asset registry
├── rules/                 # Repo-wide agent rules
├── skills/                # Task playbooks and setup helpers
├── mcp/                   # Shared MCP source and docs, if used
├── scripts/               # Validation and maintenance tooling
└── workspace/              # Ephemeral session scratch (gitignored)
    └── README.md           # Workspace conventions (tracked)
\```

Keep durable assets in the tracked directories above. Put temporary payloads, draft prompts, and other throwaway artifacts under `.agents/workspace/` instead of the `.agents/` root.

Add `.agents/mcp/` only when this repo needs a shared MCP server or local tool surface.

## Shared Assets

- Shared rules: `.agents/rules/`
- Shared skills: `.agents/skills/`
- Shared MCP source: `.agents/mcp/` when this repo needs an agent-facing service
- Shared asset manifest: `.agents/manifest.json`
- Shared validation command: `python3 .agents/scripts/validate-agent-assets.py`
- Ephemeral session scratch: `.agents/workspace/` (see `.agents/workspace/README.md`)

Tool-specific folders such as `.codex/` and `.cursor/` should be thin adapters or symlinks to `.agents/` wherever possible. Avoid duplicating rule, skill, or MCP content in multiple tool folders.

<!-- List only the adapters actually wired up for this repo, e.g.: -->
<!-- - **Codex** reads the root `AGENTS.md` natively, which is a short pointer file to this guide — no separate `.codex/` folder is needed. -->
<!-- - **Cursor** reads rules from `.cursor/rules`, which is a symlink to `.agents/rules` so shared rule content is never duplicated. -->

When adding support for another agent surface, prefer the same pattern:

1. Keep shared instructions, skills, rules, tools, and MCP code under `.agents/`.
2. Expose the shared asset through that tool's native entrypoint or config.
3. Use a symlink or the smallest possible wrapper when the tool cannot read `.agents/` directly.
4. Keep tool-specific behavior in the adapter only when the tool genuinely needs it.
5. Update every applicable adapter for the asset in the same change.
6. Update `.agents/manifest.json` with the source path, docs, adapter coverage, and any exposed tool names.

If a subtree needs different instructions, add the closest scoped `AGENTS.md` for that subtree and keep it limited to the local override. The nearest `AGENTS.md` should be treated as the more specific instruction source for files under that subtree.

## Rules

Before working in this repo, read every rule file under `.agents/rules/*`.

Treat rules with `alwaysApply: true` as baseline instructions for every task. Use rules with `alwaysApply: false` when their title, description, or content matches the task.

## Manifest and Validation

`.agents/manifest.json` lists each shared guide, rule, skill, MCP server, config adapter, and the hosts that consume it. Keep this manifest current whenever adding, moving, or exposing an agent asset.

When changing a shared asset, update every applicable host adapter in the same change. `adapter_hosts` records which hosts need direct adapter coverage; omit a host only when it consumes the asset indirectly or the asset is genuinely not applicable to that host.

Run validation before reporting shared agent asset work complete:

```bash
python3 .agents/scripts/validate-agent-assets.py --mode adapters
```

For a full validation pass that also checks Python compile, run:

```bash
python3 .agents/scripts/validate-agent-assets.py
```

If you only need to inspect MCP startup behavior after adding a server, use:

```bash
python3 .agents/scripts/validate-agent-assets.py --mode mcp
```

## Skills

For quick setup of this shared-agent layout in a new project, use:

- `.agents/skills/agents-bootstrap/SKILL.md`

The source of truth for skills is `.agents/skills/`. If a tool needs a separate install location or symlink, keep that as a thin adapter only.

## Self-Improvement Boundary

Do not make every application-code change trigger agent asset changes. Instead, when a shared asset is used and the workflow reveals friction, improve the closest shared asset that owns that behavior. Examples of real friction include slow or noisy output, fragile request construction, missing guards, unclear docs, stale templates, incorrect metadata, or repeated manual steps.
```

### `.agents/manifest.json`

Start from this minimal set and add entries only for assets that really exist in this repo:

```json
{
  "schema_version": 1,
  "validation_command": "python3 .agents/scripts/validate-agent-assets.py",
  "hosts": ["codex", "cursor", "claude"],
  "assets": [
    {
      "id": "agent-guide",
      "kind": "guide",
      "source": ".agents/README.md",
      "hosts": ["codex", "cursor", "claude"],
      "docs": [".agents/README.md"]
    },
    {
      "id": "rule-agent-asset-maintenance",
      "kind": "rule",
      "source": ".agents/rules/agent-asset-maintenance.md",
      "hosts": ["codex", "cursor", "claude"],
      "docs": [".agents/rules/agent-asset-maintenance.md"]
    },
    {
      "id": "skill-agents-bootstrap",
      "kind": "skill",
      "source": ".agents/skills/agents-bootstrap/SKILL.md",
      "hosts": ["codex", "cursor", "claude"],
      "docs": [".agents/skills/agents-bootstrap/SKILL.md"]
    }
  ],
  "mcp_startups": []
}
```

Trim `"hosts"` at the top level and per-asset to only the tools actually in use (see Step 0). Only include the `env-template` asset (pointing at `.agents/.env.example`) if Step 0 determined one is needed:

```json
{
  "id": "env-template",
  "kind": "config",
  "source": ".agents/.env.example",
  "hosts": ["codex", "cursor"],
  "docs": [".agents/README.md"]
}
```

### `.agents/rules/agent-asset-maintenance.md`

This file is static — copy it verbatim, no substitution needed:

```markdown
---
description: Shared agent asset improvement rules for {{PROJECT_NAME}}
alwaysApply: false
---

# Agent Asset Maintenance Rules

Apply this rule when using, debugging, modifying, or adding shared agent assets under `.agents/`, including skills, tools, rules, MCP servers, adapters, and their documentation.

## Continuous Improvement

When a shared agent asset is used and the actual workflow reveals repeated token waste, slow responses, noisy output, fragile request construction, brittle instructions, missing debugging ergonomics, or repeated manual steps, it may enhance itself by turning that learning into a durable improvement in its own code, instructions, tools, examples, or docs. If the learning belongs elsewhere, update the closest shared asset that owns the behavior.

Do not change shared agent assets just because a related solution, module, or code path changed elsewhere. Do not make every application-code change trigger agent asset changes. Instead, when an asset is used and the workflow reveals friction, optimize that asset. That is the intended self-improving loop.

Improve an asset only when that asset is being used or maintained and the learning affects its surface or instructions.

Useful improvements can include:

- Smaller default responses, summary-first modes, field selection, pagination helpers, response caps, or redaction.
- New focused tools or skill steps for common debugging paths.
- Safer request builders, dry-run/normalize modes, or clearer mutation guards.
- Updated README guidance, examples, rules, or skills that reduce repeated manual work.
- Shared-source updates under `.agents/` with thin `.codex/` and `.cursor/` adapters where tool-specific exposure is needed.
- Manifest updates in `.agents/manifest.json` when shared assets, host adapters, or MCP tool surfaces are added, moved, renamed, or removed.
- Ephemeral session artifacts (draft prompts, scratch notes, MCP args) under `.agents/workspace/`, not at the `.agents/` root.

## Standard Entrypoints

Prefer open or tool-recognized entrypoints over proprietary duplication. For
repo-wide coding-agent instructions, keep root `AGENTS.md` as the predictable
entrypoint and keep the substantive source in `.agents/README.md` through a
symlink or thin compatibility file.

For additional tools, expose `.agents/` assets through that tool's native config
or discovery path, but keep the adapter as small as possible. If a subtree needs
local overrides, use the closest scoped `AGENTS.md` and keep it limited to the
subtree-specific delta.

## Compatibility

Preserve existing functionality unless the user explicitly requests a breaking change.

- Keep exact/raw output available when a compact default is added.
- Keep tool names and argument compatibility where feasible.
- Keep Codex and Cursor behavior in parity unless there is a deliberate tool-specific reason for a split.
- When a shared asset changes, update every applicable adapter for that asset in the same change. Use `.agents/manifest.json` `adapter_hosts` as the source of truth; if a host is no longer applicable, update the manifest and explain why.
- Never commit tokens or secrets in config, server code, skills, rules, examples, or docs.
- Keep unrelated worktree edits untouched.

## Validation

Before reporting a shared agent asset change as complete, validate the affected behavior thoroughly:

1. Run syntax/compile checks for changed executable code.
2. For MCP servers, verify `initialize` and `tools/list` through the configured adapter path.
3. Exercise at least one representative existing workflow to check backward compatibility.
4. Exercise each new or changed tool, skill path, rule behavior, or helper, including compact/default behavior and exact/raw fallback when applicable.
5. For live services, prefer read-only validation; require explicit user approval for mutating calls.
6. If both Codex and Cursor adapters expose the asset, verify both adapter paths or explain why one could not be validated.
7. Update the relevant README, skill, rule, or tool guidance that future agents should use.
8. Run `python3 .agents/scripts/validate-agent-assets.py` for full validation, or at minimum `python3 .agents/scripts/validate-agent-assets.py --mode adapters` for adapter-only drift checks when the change is documentation-only.
```

### `.agents/workspace/README.md`

Static — copy verbatim:

```markdown
# Agent Workspace

Ephemeral scratch space for agent sessions. Put temporary payloads, draft prompts,
MCP call args, and other one-off artifacts here — not at the `.agents/` root.

## Layout

- `prompts/` — draft agent prompts and extracted notes
- `mcp/` — MCP invocation args and request/response scratch files
- `drafts/` — in-progress notes or review comments

Create additional subfolders as needed for a task. Prefer descriptive names and
date prefixes when keeping artifacts longer than a single session.

## Rules

- Do not commit workspace contents; they are gitignored except this README.
- Do not treat files here as shared agent assets. Durable skills, rules, MCP
  code, and docs belong under `.agents/skills/`, `.agents/rules/`, `.agents/mcp/`,
  or the relevant skill `references/` directory.
- Delete or archive stale files periodically so local workspace stays small.
```

### `.agents/skills/agents-bootstrap/SKILL.md`

Copy this entire skill file into the new repo verbatim, so the bootstrap capability travels with the project and future agents in that repo can re-run or extend it without depending on this or any other source repo.

### `.agents/scripts/validate-agent-assets.py`

Copy verbatim from `references/validate-agent-assets.py` next to this skill. It's a standalone Python script that only validates the `.agents/` folder's own structure (manifest correctness, adapter symlinks, no stray root files, and that any `.py` files under `.agents/` itself compile) — it never inspects or assumes anything about the host project's language, build system, or dependencies, so it works unmodified in any repo.

### `.agents/.env.example` (only if Step 0 determined it's needed)

```
# Copy this file to .agents/.env.local for optional local overrides.
# .agents/.env.local is ignored by Git.
#
# {{PROJECT_NAME}} does not require secrets for normal agent workflows.
# Add local-only variables here if a future MCP server or tool needs them.
```

## Step 3: Wire Up Adapters

Only for the tools identified in Step 0:

- **Codex** — needs nothing beyond the root `AGENTS.md` created above; Codex reads it natively.
- **Cursor** — create a symlink so rule content is never duplicated:
  ```bash
  mkdir -p .cursor
  ln -s ../.agents/rules .cursor/rules
  ```
- **Any other tool** — expose the shared asset through that tool's native entrypoint or config, using a symlink or the smallest possible wrapper. Never copy rule/skill content into a tool folder.

After wiring adapters, uncomment/fill in the adapter bullet list in `.agents/README.md`'s "Shared Assets" section to name exactly what's wired up (see the commented example in the template above).

## Step 4: Update `.gitignore`

Append (don't overwrite existing entries):

```
/.agents/workspace/*
!/.agents/workspace/README.md
```

Add `/.agents/.env.local` too if Step 0 determined an env template is needed.

## Step 5: Validate

```bash
python3 .agents/scripts/validate-agent-assets.py --mode adapters
python3 .agents/scripts/validate-agent-assets.py
```

Fix any `FAIL` lines before considering the bootstrap complete — most commonly a manifest `source`/`doc` path that doesn't exist yet, or a `.cursor/rules` adapter that isn't a symlink.

## Manifest Rules

- Every asset in `.agents/manifest.json` should match files that really exist.
- `adapter_hosts` should only list hosts that truly need direct adapter coverage.
- If a host does not need a shared asset, omit it instead of keeping a stale placeholder.
- Keep docs and validation commands aligned with the files that are actually present.

## Finish Line

A bootstrap is complete when:

- `AGENTS.md` exists at the repo root and names the project.
- `.agents/README.md` names the correct project and lists only the adapters actually wired up.
- `.agents/manifest.json` contains only live assets, scoped to the hosts actually in use.
- Every requested tool adapter (Codex/Cursor/other) is wired as a thin pointer or symlink, never a content copy.
- The validation command passes with no `FAIL` lines.
- The next person can read this skill alone — without access to any other repo — and reproduce the same setup from scratch.
