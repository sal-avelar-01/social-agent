# linkedin-agent

Automated LinkedIn content agent for Sal Avelar — Head of Marketing at FulfillmentIQ.
Reads source material from Notion, generates posts in Sal's voice via Claude API,
syncs engagement from Buffer, and runs a weekly learning loop. Deployed via GitHub Actions.

## Architecture

```
Notion Source Inbox (Status=New)
        ↓ generate.py (daily, Mon–Fri)
Notion LinkedIn Posts DB (Draft Ready)
        ↓ you review → Approved
Buffer queue (push_to_buffer.py)
        ↓ posted to LinkedIn
sync_engagement.py (weekday evenings)
        ↓ engagement stats → Notion
learn.py (Sunday)
        ↓ pattern analysis
prompts/learned_patterns.md (committed to repo)
        ↓ injected into next generation
```

## Key files

| File | Purpose |
|------|---------|
| `agent/generate.py` | Daily generation: reads Notion → calls Claude → writes drafts |
| `agent/learn.py` | Weekly learning: top performers → pattern analysis → learned_patterns.md |
| `agent/sync_engagement.py` | Buffer analytics → Notion engagement fields |
| `agent/push_to_buffer.py` | Notion Approved posts → Buffer queue |
| `agent/notion_client.py` | All Notion API calls + field extractors (single source of truth) |
| `agent/buffer_client.py` | All Buffer REST API calls |
| `prompts/voice_prompt.md` | Sal's full voice profile — do not modify without deliberate intent |
| `prompts/system_prompt.py` | Builds Claude system + user prompts dynamically |
| `prompts/learned_patterns.md` | AUTO-GENERATED weekly by learn.py — never edit manually |
| `scripts/setup_posts_db.py` | One-time: creates LinkedIn Posts DB in Notion |

## Notion databases

| DB | ID | Purpose |
|----|-----|---------|
| Source Inbox | `31b00cfe6b7880f1b015d9d66172cd74` | Raw source material |
| LinkedIn Posts | Set via `NOTION_POSTS_DB_ID` env var | Generated drafts + engagement |

### Source Inbox field names (exact, case-sensitive)
`Name`, `Excerpt / Notes`, `Pillar`, `Tags`, `Status`, `Tier`, `Source`, `URL`, `Captured At`

### Source Inbox field values
- **Status**: `New` → `Used` → `Ignored`
- **Tier**: `0` (low), `1` (standard), `2` (high) — agent processes higher tiers first
- **Pillar**: `Growth Systems`, `Monetization`, `Retention`, `Acquisition`, `Activation`, `Strategy`

### LinkedIn Posts field names (exact, case-sensitive)
`Name`, `Generated Post`, `Status`, `Pillar`, `Format`, `Tone`, `Post Date`,
`Impressions`, `Likes`, `Comments`, `Shares`, `Engagement Score`,
`Top Performer`, `What Worked`, `Source Name`, `Source Pillar`

### LinkedIn Posts field values
- **Status**: `Draft Ready` → `Approved` → `Posted`
- **Format**: `default`, `experiment_brief`, `teardown`, `readout`, `loop`
- **Tone**: `Thought leadership`, `Provocative`, `Data-driven`, `Story`, `Artifact`

## Engagement scoring
```
score = likes + (comments × 3) + (shares × 5)
Top Performer threshold: score ≥ 50 (configurable via ENGAGEMENT_THRESHOLD)
```

## Environment variables

```
ANTHROPIC_API_KEY
NOTION_API_KEY
NOTION_SOURCE_DB_ID    # Source Inbox — 31b00cfe6b7880f1b015d9d66172cd74
NOTION_POSTS_DB_ID     # LinkedIn Posts — from setup_posts_db.py
BUFFER_ACCESS_TOKEN
BUFFER_PROFILE_ID      # LinkedIn profile ID in Buffer
POSTS_PER_RUN          # default 3
POST_FORMAT            # default | experiment_brief | teardown | readout | loop
ENGAGEMENT_THRESHOLD   # default 50
```

## Run commands

```bash
pip install -r requirements.txt

python agent/generate.py           # generate posts from Source Inbox
python agent/sync_engagement.py    # pull Buffer stats → Notion
python agent/push_to_buffer.py     # push Approved posts → Buffer queue
python agent/learn.py              # weekly pattern analysis
python scripts/setup_posts_db.py   # one-time Notion DB creation
python agent/buffer_client.py profiles  # find your BUFFER_PROFILE_ID
```

## GitHub Actions workflows

| Workflow | Schedule | What it does |
|----------|----------|-------------|
| `daily-posts.yml` | Mon–Fri 7am EST | Runs generate.py |
| `sync-and-push.yml` | Weekdays 6pm EST | Syncs Buffer stats + pushes Approved posts |
| `weekly-learning.yml` | Sunday 10am EST | Runs learn.py, commits learned_patterns.md |

## Critical rules

- **Never edit** `prompts/learned_patterns.md` — overwritten automatically every Sunday
- **Never commit** `.env` or `data/engagement.csv`
- **Notion field names are case-sensitive** — match exactly as listed above
- **Buffer profile ID** is the LinkedIn channel ID inside Buffer, not your LinkedIn ID
- When modifying `notion_client.py`, update both the read and write methods together
- The `prompts/` directory is a Python package (`__init__.py` present) — imports work as `from prompts.system_prompt import ...`

## Voice

Sal's voice is defined in `prompts/voice_prompt.md`. Key traits:
- Skeptical-but-bullish growth marketer, 42, operator with scars
- Calls out lazy work (patterns, not people)
- Warmly direct, measurement-literate, artifact-first
- Banned words: unlock, seamless, robust, revolutionary, leverage (verb), delve
- Default structure: Hook → Diagnosis → Model → Steps → Failure modes → Close
