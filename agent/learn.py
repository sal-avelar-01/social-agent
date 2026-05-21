"""
learn.py — Weekly learning engine.

Pulls all Top Performer posts from the LinkedIn Posts DB, sends them to Claude
for pattern analysis, and writes the findings to prompts/learned_patterns.md.
That file is committed back to the repo by GitHub Actions and injected into
every subsequent generation call.

Run:   python agent/learn.py
Env:   NOTION_API_KEY, NOTION_SOURCE_DB_ID, NOTION_POSTS_DB_ID, ANTHROPIC_API_KEY
       MIN_POSTS_TO_LEARN (optional, default 3)
"""

import os
import sys
import json
import anthropic
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.notion_client import NotionClient, extract_post_fields

MIN_POSTS = int(os.environ.get("MIN_POSTS_TO_LEARN", "3"))
PATTERNS_FILE = Path(__file__).parent.parent / "prompts" / "learned_patterns.md"
LOG_FILE = Path(__file__).parent.parent / "data" / "performance_log.json"


def build_analysis_prompt(posts: list[dict]) -> str:
    posts_text = "\n\n---\n\n".join([
        (
            f"RANK {i+1} | SCORE: {p['score']} | PILLAR: {p['pillar']} "
            f"| FORMAT: {p['format']} | TONE: {p['tone']}\n"
            f"IMPRESSIONS: {p['impressions']} | LIKES: {p['likes']} "
            f"| COMMENTS: {p['comments']} | SHARES: {p['shares']}\n\n"
            f"{p['post']}"
        )
        for i, p in enumerate(posts)
    ])

    return f"""You are analyzing LinkedIn posts written by Sal — a skeptical growth marketer — \
to extract what's working so future posts can be calibrated to perform better.

You have {len(posts)} top-performing posts, ordered by engagement score (highest first).
Engagement score = Likes + (Comments × 3) + (Shares × 5).
Comments and shares are weighted higher because they signal quality, not just reach.

{posts_text}

---

Analyze these posts and return a structured markdown document covering:

## 1. Hook Patterns
What types of openers generate the most engagement?
Quote specific opening lines. What structural/tonal patterns do the best hooks share?
(e.g. "call out a mistake", "confession", "contrarian opener")

## 2. Format Performance
Which formats (default narrative, experiment_brief, teardown, readout, loop) are performing best?
Any interaction between format and pillar?

## 3. Pillar Performance
Which content pillars (Growth Systems, Monetization, Retention, Acquisition, Activation, Strategy)
are resonating most? Which are underperforming?

## 4. Length & Structure
What word counts and structural patterns show up in high-scorers vs low-scorers?

## 5. Voice & Texture Signals
Which specific words, phrases, or stylistic choices appear most in high-performers?
What's notably absent or weak in lower-scoring posts?

## 6. Engagement Type Patterns
Are comments (debate/opinion signal) clustering around specific post types?
Are shares (utility/artifact signal) clustering around others?

## 7. Do More Of
3–5 specific, actionable recommendations for the next 30 posts.

## 8. Do Less Of
2–3 patterns from lower-scoring posts to avoid.

Be specific. Quote from the posts. Give percentages or counts where you can.
This output will be injected directly into future generation prompts, so write it
as clear, directive guidance — not a report.
"""


def extract_patterns(posts: list[dict]) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": build_analysis_prompt(posts)}],
    )
    return message.content[0].text.strip()


def update_log(posts: list[dict]):
    log = []
    if LOG_FILE.exists():
        try:
            log = json.loads(LOG_FILE.read_text())
        except Exception:
            log = []

    entry = {
        "date": str(date.today()),
        "posts_analyzed": len(posts),
        "top_post_name": posts[0]["name"] if posts else None,
        "top_score": posts[0]["score"] if posts else 0,
        "avg_score": round(sum(p["score"] for p in posts) / len(posts), 1) if posts else 0,
    }
    log.append(entry)
    LOG_FILE.write_text(json.dumps(log, indent=2))


def run():
    print(f"🧠 Weekly Learning Run — {date.today()}\n")

    notion = NotionClient()

    print("Fetching top performers from LinkedIn Posts DB...")
    pages = notion.get_top_performers(limit=30)

    if not pages:
        print("⚠️  No top performers found yet. Posts need Status=Posted and Top Performer=✓.")
        print("   Tip: lower ENGAGEMENT_THRESHOLD in .env if your audience is still growing.")
        return

    posts = [extract_post_fields(p) for p in pages]
    posts = [p for p in posts if p["post"]]  # skip empty posts

    if len(posts) < MIN_POSTS:
        print(f"⚠️  Only {len(posts)} usable top performers. Need at least {MIN_POSTS}. Skipping.")
        print("   Keep posting and syncing engagement — the learning loop will activate soon.")
        return

    print(f"📊 Analyzing {len(posts)} top performers with Claude...\n")
    patterns = extract_patterns(posts)

    # Write patterns file
    header = (
        f"# Learned Patterns — Auto-generated {date.today()}\n"
        f"> Updated weekly by learn.py. Do not edit manually.\n"
        f"> Based on analysis of {len(posts)} top-performing posts.\n\n"
    )
    PATTERNS_FILE.write_text(header + patterns)
    print(f"✅ prompts/learned_patterns.md updated")

    # Update audit log
    update_log(posts)
    print(f"📝 data/performance_log.json updated")

    # Print quick summary
    print(f"\n📈 Quick stats:")
    print(f"   Posts analyzed: {len(posts)}")
    print(f"   Top score: {posts[0]['score']} ({posts[0]['name'][:60]})")
    print(f"   Avg score: {sum(p['score'] for p in posts) / len(posts):.1f}")
    by_pillar = {}
    for p in posts:
        by_pillar[p["pillar"]] = by_pillar.get(p["pillar"], 0) + 1
    print(f"   By pillar: {by_pillar}")


if __name__ == "__main__":
    run()
