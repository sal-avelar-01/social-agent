# LinkedIn Agent — Sal's Post Generator

A self-improving LinkedIn content agent that reads from a Notion Source Inbox,
generates posts in Sal's voice using Claude, and learns from engagement data over time.

---

## How It Works

```
Source Inbox (Notion)
        ↓ Status = New, sorted by Tier
  generate.py (daily, Mon–Fri)
        ↓ Claude API
  LinkedIn Posts DB (Notion)
        ↓ You review → approve → post
  sync_engagement.py (weekly, manual)
        ↓ Update Posts DB with real numbers
  learn.py (Sunday auto-run)
        ↓ Claude analyzes top performers
  prompts/learned_patterns.md
        ↓ Injected into next generation run
  Better posts
```

---

## One-Time Setup (do this first)

### 1. Create a Notion Integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Create a new integration → name it `linkedin-agent`
3. Copy the **Internal Integration Token** (`secret_xxxx`)
4. Share **both** Notion databases with this integration:
   - Open each database → `•••` menu → `Connections` → Add your integration

### 2. Create the LinkedIn Posts Database

```bash
export NOTION_API_KEY=secret_xxxx
python scripts/setup_posts_db.py
```

Follow the prompts. It will print your `NOTION_POSTS_DB_ID` when done.

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual keys
```

Your Source Inbox DB ID is already pre-filled: `31b00cfe6b7880f1b015d9d66172cd74`

### 4. Add GitHub Secrets

In your GitHub repo → **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|--------|-------|
| `NOTION_API_KEY` | `secret_xxxx` |
| `NOTION_SOURCE_DB_ID` | `31b00cfe6b7880f1b015d9d66172cd74` |
| `NOTION_POSTS_DB_ID` | (from step 2) |
| `ANTHROPIC_API_KEY` | `sk-ant-xxxx` |

### 5. Test Locally

```bash
pip install -r requirements.txt
python agent/generate.py
```

Check your LinkedIn Posts DB in Notion — you should see Draft Ready entries.

---

## Daily Workflow

1. **Agent generates 3 drafts** every weekday at 7am EST (automatic)
2. **You review** in the LinkedIn Posts DB → flip Status to `Approved`
3. **Copy/paste** the approved post to LinkedIn → flip Status to `Posted`
4. That's it

---

## Weekly Learning Loop

### Sync engagement (do this once a week)

1. Go to LinkedIn → Analytics → Export post data as CSV
2. Rename/format to match: `name, impressions, likes, comments, shares`
3. Save as `data/engagement.csv`
4. Run:

```bash
python agent/sync_engagement.py
```

Or trigger the learning run manually from GitHub Actions → **Weekly Learning Run** → **Run workflow**.

### What the agent learns

Every Sunday, `learn.py` runs automatically and:
- Pulls all posts with `Top Performer = ✓` from the Posts DB
- Sends them to Claude for pattern analysis
- Writes findings to `prompts/learned_patterns.md`
- Commits and pushes the file to the repo
- Next generation run injects those patterns into every prompt

---

## Notion Source Inbox Fields

| Field | Purpose |
|-------|---------|
| `Name` | Title / post hook idea |
| `Excerpt / Notes` | Your raw notes, article excerpts, data points |
| `Pillar` | Growth Systems / Monetization / Retention / Acquisition / Activation / Strategy |
| `Tags` | Article / Video / Tutorial / Research / Reference / News / Analysis / Guide / Review |
| `Tier` | 0 = low priority, 1 = standard, 2 = high priority |
| `Status` | **New** → agent processes → **Used** (or set to **Ignored** to skip) |
| `Source` | Where the idea came from |
| `URL` | Source URL (included in generation context) |

**Pro tip:** Set `Tier = 2` for your best material — the agent processes higher tiers first.

---

## LinkedIn Posts DB Fields

| Field | Purpose |
|-------|---------|
| `Name` | Post title (copied from source) |
| `Generated Post` | The draft post text |
| `Status` | Draft Ready → Approved → Posted |
| `Pillar` | Content pillar |
| `Format` | default / experiment_brief / teardown / readout / loop |
| `Tone` | Thought leadership / Provocative / Data-driven / Story / Artifact |
| `Post Date` | When you intend to post |
| `Impressions / Likes / Comments / Shares` | Filled by sync_engagement.py |
| `Engagement Score` | Auto-computed: likes + (comments×3) + (shares×5) |
| `Top Performer` | Auto-checked when score ≥ threshold |
| `What Worked` | Optional manual notes for the learning loop |

---

## Configuration

All settings are in `.env` (local) or GitHub Secrets (CI):

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTS_PER_RUN` | `3` | Posts generated per daily run |
| `POST_FORMAT` | `default` | Format type for all posts in run |
| `POST_TONE` | `Thought leadership` | Default tone |
| `ENGAGEMENT_THRESHOLD` | `50` | Score needed to be a Top Performer |
| `MIN_POSTS_TO_LEARN` | `3` | Min top performers before learn.py activates |

---

## Post Formats

| Format | When to use |
|--------|-------------|
| `default` | Hook → Diagnosis → Model → Steps → Failure modes → Close |
| `experiment_brief` | Sharing a real test: Goal / Baseline / Hypothesis / Method / Risks |
| `teardown` | Deconstructing an offer, strategy, or channel |
| `readout` | Sharing results: what happened, what surprised, what changed |
| `loop` | Mapping a growth loop: trigger → action → reward → repeat |

Override per-run:
```bash
POST_FORMAT=experiment_brief python agent/generate.py
```

Or use the workflow_dispatch inputs in GitHub Actions.

---

## Learning Timeline

| Posts Published | What the Agent Has |
|----------------|-------------------|
| 0–10 | Voice profile only (already high quality) |
| 10–25 | First pattern file — weights winning formats |
| 25–50 | Pillar-level few-shot examples — sharper calibration |
| 50–100 | Strong signal on hooks, format × pillar combos |
| 100+ | Hard to distinguish from your best work |

---

## File Structure

```
linkedin-agent/
├── .github/workflows/
│   ├── daily-posts.yml        # Mon–Fri, 7am EST
│   └── weekly-learning.yml    # Sunday, 10am EST (auto-commits patterns)
├── agent/
│   ├── generate.py            # Daily generation run
│   ├── learn.py               # Weekly pattern analysis
│   ├── sync_engagement.py     # Engagement CSV → Notion
│   └── notion_client.py       # Shared Notion API helpers
├── prompts/
│   ├── voice_prompt.md        # Sal's voice profile (edit to refine)
│   ├── system_prompt.py       # Builds Claude system prompt dynamically
│   └── learned_patterns.md    # Auto-generated weekly (do not edit)
├── data/
│   ├── engagement_sample.csv  # CSV format template
│   └── performance_log.json   # Audit trail (auto-generated)
├── scripts/
│   └── setup_posts_db.py      # One-time Notion DB creation
├── .env.example
├── requirements.txt
└── README.md
```

---

## Troubleshooting

**"No new sources found"**
→ Check Source Inbox in Notion — items need `Status = New`

**"Notion API 401 error"**
→ Check NOTION_API_KEY is correct and integration is shared with both databases

**"learn.py: Not enough top performers"**
→ Lower `ENGAGEMENT_THRESHOLD` in .env if your audience is still growing
→ Or manually check `Top Performer` on your best posts

**"weekly-learning workflow not committing"**
→ Check the workflow has `permissions: contents: write` in the YAML
→ Make sure GitHub Actions has write access: Settings → Actions → General → Workflow permissions → Read and write
