"""
sync_engagement.py — Sync Buffer post analytics → Notion LinkedIn Posts DB.

Replaces the manual CSV approach. Pulls sent post stats directly from Buffer's
API, fuzzy-matches against Notion post names, and updates engagement fields.

Run weekly (or manually after checking Buffer):
  python agent/sync_engagement.py

Env vars:
  NOTION_API_KEY, NOTION_SOURCE_DB_ID, NOTION_POSTS_DB_ID
  BUFFER_ACCESS_TOKEN, BUFFER_PROFILE_ID
  ENGAGEMENT_THRESHOLD (optional, default 50)
"""

import os
import sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.notion_client import NotionClient, extract_post_fields
from agent.buffer_client import BufferClient

# How similar a Buffer text preview must be to a Notion post name to match
MATCH_THRESHOLD = float(os.environ.get("MATCH_THRESHOLD", "0.45"))


def similarity(a: str, b: str) -> float:
    """Ratio of how similar two strings are (0.0 → 1.0)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def find_best_match(buffer_preview: str, notion_pages: list[dict]) -> tuple[dict | None, float]:
    """
    Match a Buffer text preview against Notion post names.
    Returns (best_page_dict, score) or (None, 0.0) if no good match.

    Strategy:
      1. Exact substring match (Buffer preview often truncated at 80 chars)
      2. Sequence similarity fallback
    """
    best_page = None
    best_score = 0.0

    for page in notion_pages:
        name = page["name"].lower().strip()
        preview = buffer_preview.lower().strip()

        # Substring check: does the Notion name start with the Buffer preview?
        # (Buffer truncates at ~80 chars, Notion stores the full topic/title)
        if preview and (name.startswith(preview[:40]) or preview[:40] in name):
            return page, 1.0

        # Fallback: sequence similarity
        score = similarity(preview, name)
        if score > best_score:
            best_score = score
            best_page = page

    return (best_page, best_score) if best_score >= MATCH_THRESHOLD else (None, 0.0)


def run():
    print("📊 Buffer → Notion Engagement Sync\n")

    buffer = BufferClient()
    notion = NotionClient()

    # 1. Load all posted Notion pages
    print("Fetching posted pages from Notion Posts DB...")
    raw_pages = notion.get_posted_pages()
    notion_pages = [extract_post_fields(p) for p in raw_pages]
    print(f"  Found {len(notion_pages)} posted page(s)\n")

    # 2. Pull sent posts from Buffer
    print("Fetching sent updates from Buffer...")
    updates = buffer.get_all_sent_updates(max_pages=5)
    print(f"  Found {len(updates)} sent update(s)\n")

    if not updates:
        print("⚠️  No sent updates found in Buffer.")
        print("   Check that BUFFER_PROFILE_ID matches your LinkedIn profile.")
        return

    # 3. Match and update
    matched = 0
    unmatched = []
    threshold = int(os.environ.get("ENGAGEMENT_THRESHOLD", "50"))

    print("Matching Buffer posts to Notion pages...\n")

    for update in updates:
        stats = buffer.extract_stats(update)
        preview = stats["text_preview"]

        page, score = find_best_match(preview, notion_pages)

        if not page:
            unmatched.append(preview[:60])
            continue

        try:
            eng_score = notion.update_engagement(
                page_id=page["id"],
                impressions=stats["impressions"],
                likes=stats["likes"],
                comments=stats["comments"],
                shares=stats["shares"],
            )
            top_flag = "⭐ TOP PERFORMER" if eng_score >= threshold else ""
            print(f"  ✅ {preview[:55]}...")
            print(
                f"     Score: {eng_score} | "
                f"👁 {stats['impressions']:,} | "
                f"👍 {stats['likes']} | "
                f"💬 {stats['comments']} | "
                f"🔁 {stats['shares']} "
                f"{top_flag}"
            )
            matched += 1

        except Exception as e:
            print(f"  ❌ Error updating '{preview[:50]}': {e}")

    # 4. Summary
    print(f"\n📈 Sync complete: {matched} matched, {len(unmatched)} unmatched")

    if unmatched:
        print("\n⚠️  Could not match these Buffer posts to Notion pages:")
        for u in unmatched:
            print(f"   - {u}")
        print(
            "\n   Fix: make sure the Notion 'Name' field contains keywords from "
            "the start of your LinkedIn post. Or lower MATCH_THRESHOLD (default 0.45)."
        )


if __name__ == "__main__":
    run()
