# Local context — Sal Avelar
# This file is gitignored. Add personal notes, credentials reminders,
# and session learnings here. Never commit this file.

## My setup

- Notion workspace: sauloavelar
- Buffer account: connected via MCP in Claude.ai + REST API in GitHub Actions
- GitHub repo: linkedin-agent
- Local dev: run scripts from repo root with .env loaded

## Credentials locations

- .env file: repo root (gitignored)
- GitHub Secrets: Settings → Secrets → Actions (4 required: see CLAUDE.md)
- Notion integration: notion.so/my-integrations → linkedin-agent integration
- Buffer token: buffer.com/developers/apps

## My Notion database URLs

- Source Inbox: https://www.notion.so/sauloavelar/31b00cfe6b7880f1b015d9d66172cd74
- LinkedIn Posts: (add URL after running setup_posts_db.py)

## Personal workflow

1. Add ideas to Source Inbox in Notion (set Tier=2 for strong material)
2. Agent generates 3 drafts each weekday morning (7am EST)
3. Review drafts in LinkedIn Posts DB → flip to Approved
4. Agent pushes Approved posts to Buffer at 6pm EST
5. Sync engagement weekly after checking Buffer Analytics
6. Learning loop runs Sunday — check prompts/learned_patterns.md after

## Post format preferences (override POST_FORMAT env var when needed)

- Monday/Wednesday: default narrative
- Tuesday/Thursday: experiment_brief or teardown (artifact-heavy)
- Friday: readout or loop (lower friction, higher shareability)

## Things I've learned / session notes

- Post #1 (Claude billing, 89.7k impressions) — personal + specific dollar amount + quiet confession = viral formula. Replicate.
- Posts with zero engagement (#8, #9) were too "professional" — no hook, no texture, no scar. Avoid.
- Engagement rate ≠ reach. High early engagement velocity is what triggers LinkedIn algorithm amplification.
- Tier 2 sources should be genuinely strong material only — don't over-promote mediocre ideas

## Reminders

- Check learned_patterns.md every Monday — it updates Sunday night
- MATCH_THRESHOLD=0.45 for Buffer→Notion fuzzy matching (lower if getting many unmatched)
- ENGAGEMENT_THRESHOLD=50 — recalibrate after 30 posts if audience grows significantly
- Run `python agent/buffer_client.py profiles` if BUFFER_PROFILE_ID ever needs updating
