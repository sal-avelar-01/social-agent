"""
push_to_buffer.py — Push approved Notion drafts → Buffer queue.

Polls the LinkedIn Posts DB for pages with Status = Approved,
pushes each post text to Buffer as a queued post,
then flips the Notion Status → Posted.

Run manually or hook into a GitHub Actions workflow:
  python agent/push_to_buffer.py

Env vars:
  NOTION_API_KEY, NOTION_SOURCE_DB_ID, NOTION_POSTS_DB_ID
  BUFFER_ACCESS_TOKEN, BUFFER_PROFILE_ID
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.notion_client import NotionClient
from agent.buffer_client import BufferClient

NOTION_VERSION = "2022-06-28"


def get_approved_posts(notion: NotionClient) -> list[dict]:
    """Pull all posts with Status = Approved from the Posts DB."""
    import requests
    url = f"https://api.notion.com/v1/databases/{notion.posts_db_id}/query"
    payload = {
        "filter": {"property": "Status", "select": {"equals": "Approved"}},
        "page_size": 10,
    }
    res = requests.post(url, headers=notion.headers, json=payload)
    res.raise_for_status()
    return res.json().get("results", [])


def extract_post_text(page: dict) -> tuple[str, str]:
    """Return (page_id, post_text) from a Notion page."""
    props = page["properties"]
    page_id = page["id"]
    rt = props.get("Generated Post", {}).get("rich_text", [])
    text = rt[0]["text"]["content"] if rt else ""
    name_rt = props.get("Name", {}).get("title", [])
    name = name_rt[0]["text"]["content"] if name_rt else "Untitled"
    return page_id, name, text


def mark_posted(notion: NotionClient, page_id: str):
    """Flip Status to Posted in Notion."""
    import requests
    from datetime import date
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Status": {"select": {"name": "Posted"}},
            "Post Date": {"date": {"start": str(date.today())}},
        }
    }
    res = requests.patch(url, headers=notion.headers, json=payload)
    res.raise_for_status()


def run():
    print("🚀 Notion Approved → Buffer Queue\n")

    notion = NotionClient()
    buffer = BufferClient()

    pages = get_approved_posts(notion)

    if not pages:
        print("📭 No Approved posts found in Notion Posts DB.")
        print("   Flip a post's Status to 'Approved' in Notion to queue it.")
        return

    print(f"Found {len(pages)} approved post(s)\n")

    pushed = 0
    for page in pages:
        page_id, name, text = extract_post_text(page)

        if not text:
            print(f"  ⚠️  '{name}' has no post text. Skipping.")
            continue

        print(f"  Pushing: {name[:60]}")
        print(f"  Preview: {text[:80]}...\n")

        try:
            result = buffer.create_draft(post_text=text)
            if result.get("success"):
                mark_posted(notion, page_id)
                print(f"  ✅ Added to Buffer queue. Notion status → Posted.\n")
                pushed += 1
            else:
                print(f"  ❌ Buffer returned: {result}\n")

        except Exception as e:
            print(f"  ❌ Error: {e}\n")

    print(f"✅ Done. {pushed}/{len(pages)} post(s) queued in Buffer.")


if __name__ == "__main__":
    run()
