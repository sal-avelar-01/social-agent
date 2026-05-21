"""
Shared Notion API client.
Handles all reads/writes for both the Source Inbox and LinkedIn Posts databases.
"""

import os
import requests

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"
ENGAGEMENT_THRESHOLD = int(os.environ.get("ENGAGEMENT_THRESHOLD", "50"))


class NotionClient:
    def __init__(self):
        self.key = os.environ["NOTION_API_KEY"]
        self.source_db_id = os.environ["NOTION_SOURCE_DB_ID"]  # Source Inbox
        self.posts_db_id = os.environ["NOTION_POSTS_DB_ID"]    # LinkedIn Posts
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    def _post(self, path, payload):
        res = requests.post(f"{BASE_URL}{path}", headers=self.headers, json=payload)
        res.raise_for_status()
        return res.json()

    def _patch(self, path, payload):
        res = requests.patch(f"{BASE_URL}{path}", headers=self.headers, json=payload)
        res.raise_for_status()
        return res.json()

    # ------------------------------------------------------------------
    # Source Inbox
    # ------------------------------------------------------------------

    def get_new_sources(self, limit=3):
        """
        Pull items from Source Inbox where Status = New.
        Sorted by Tier descending (2 → 1 → 0), then Captured At descending.
        """
        payload = {
            "filter": {
                "property": "Status",
                "select": {"equals": "New"},
            },
            "sorts": [
                {"property": "Tier", "direction": "descending"},
                {"property": "Captured At", "direction": "descending"},
            ],
            "page_size": limit,
        }
        data = self._post(f"/databases/{self.source_db_id}/query", payload)
        return data.get("results", [])

    def mark_source_used(self, page_id):
        """Flip Source Inbox item Status → Used after a post is generated from it."""
        self._patch(
            f"/pages/{page_id}",
            {"properties": {"Status": {"select": {"name": "Used"}}}},
        )

    # ------------------------------------------------------------------
    # LinkedIn Posts DB
    # ------------------------------------------------------------------

    def create_post(self, name, generated_post, pillar, format_type, tone,
                    source_name, source_pillar):
        """Create a Draft Ready page in the LinkedIn Posts DB."""
        # Notion rich_text cap is 2000 chars per block
        post_content = generated_post[:2000]
        props = {
            "Name": {"title": [{"text": {"content": name[:255]}}]},
            "Generated Post": {"rich_text": [{"text": {"content": post_content}}]},
            "Format": {"select": {"name": format_type}},
            "Tone": {"select": {"name": tone}},
            "Status": {"select": {"name": "Draft Ready"}},
            "Source Name": {"rich_text": [{"text": {"content": (source_name or "")[:2000]}}]},
            "Source Pillar": {"rich_text": [{"text": {"content": (source_pillar or "")[:2000]}}]},
        }
        if pillar:
            props["Pillar"] = {"select": {"name": pillar}}

        payload = {
            "parent": {"database_id": self.posts_db_id},
            "properties": props,
        }
        return self._post("/pages", payload)

    def get_top_performers(self, limit=20):
        """Pull top-performing posts (Top Performer checked + Status = Posted)."""
        payload = {
            "filter": {
                "and": [
                    {"property": "Top Performer", "checkbox": {"equals": True}},
                    {"property": "Status", "select": {"equals": "Posted"}},
                ]
            },
            "sorts": [{"property": "Engagement Score", "direction": "descending"}],
            "page_size": limit,
        }
        data = self._post(f"/databases/{self.posts_db_id}/query", payload)
        return data.get("results", [])

    def get_top_performers_by_pillar(self, pillar, limit=3):
        """Few-shot examples: top posts filtered to a specific pillar."""
        payload = {
            "filter": {
                "and": [
                    {"property": "Top Performer", "checkbox": {"equals": True}},
                    {"property": "Pillar", "select": {"equals": pillar}},
                    {"property": "Status", "select": {"equals": "Posted"}},
                ]
            },
            "sorts": [{"property": "Engagement Score", "direction": "descending"}],
            "page_size": limit,
        }
        data = self._post(f"/databases/{self.posts_db_id}/query", payload)
        return data.get("results", [])

    def get_posted_pages(self):
        """All posts with Status = Posted (used by sync_engagement)."""
        payload = {
            "filter": {"property": "Status", "select": {"equals": "Posted"}},
            "page_size": 100,
        }
        data = self._post(f"/databases/{self.posts_db_id}/query", payload)
        return data.get("results", [])

    def update_engagement(self, page_id, impressions, likes, comments, shares):
        """Write engagement numbers back to a post and compute score."""
        score = likes + (comments * 3) + (shares * 5)
        self._patch(
            f"/pages/{page_id}",
            {
                "properties": {
                    "Impressions": {"number": impressions},
                    "Likes": {"number": likes},
                    "Comments": {"number": comments},
                    "Shares": {"number": shares},
                    "Engagement Score": {"number": score},
                    "Top Performer": {"checkbox": score >= ENGAGEMENT_THRESHOLD},
                    "Status": {"select": {"name": "Posted"}},
                }
            },
        )
        return score


# ------------------------------------------------------------------
# Field extractors — keep all Notion parsing in one place
# ------------------------------------------------------------------

def extract_source_fields(page):
    """Parse a Source Inbox Notion page into a clean dict."""
    props = page["properties"]

    name_rt = props.get("Name", {}).get("title", [])
    name = name_rt[0]["text"]["content"] if name_rt else "Untitled"

    notes_rt = props.get("Excerpt / Notes", {}).get("rich_text", [])
    notes = notes_rt[0]["text"]["content"] if notes_rt else ""

    pillar_sel = props.get("Pillar", {}).get("select")
    pillar = pillar_sel["name"] if pillar_sel else ""

    tags_ms = props.get("Tags", {}).get("multi_select", [])
    tags = [t["name"] for t in tags_ms]

    source_rt = props.get("Source", {}).get("rich_text", [])
    source = source_rt[0]["text"]["content"] if source_rt else ""

    url = props.get("URL", {}).get("url") or ""

    tier_sel = props.get("Tier", {}).get("select")
    tier = tier_sel["name"] if tier_sel else "0"

    return {
        "id": page["id"],
        "name": name,
        "notes": notes,
        "pillar": pillar,
        "tags": tags,
        "source": source,
        "url": url,
        "tier": tier,
    }


def extract_post_fields(page):
    """Parse a LinkedIn Posts Notion page into a clean dict."""
    props = page["properties"]

    name_rt = props.get("Name", {}).get("title", [])
    name = name_rt[0]["text"]["content"] if name_rt else "Untitled"

    post_rt = props.get("Generated Post", {}).get("rich_text", [])
    post = post_rt[0]["text"]["content"] if post_rt else ""

    pillar_sel = props.get("Pillar", {}).get("select")
    pillar = pillar_sel["name"] if pillar_sel else ""

    format_sel = props.get("Format", {}).get("select")
    format_type = format_sel["name"] if format_sel else "default"

    tone_sel = props.get("Tone", {}).get("select")
    tone = tone_sel["name"] if tone_sel else ""

    impressions = props.get("Impressions", {}).get("number") or 0
    likes = props.get("Likes", {}).get("number") or 0
    comments = props.get("Comments", {}).get("number") or 0
    shares = props.get("Shares", {}).get("number") or 0
    score = likes + (comments * 3) + (shares * 5)

    return {
        "id": page["id"],
        "name": name,
        "post": post,
        "pillar": pillar,
        "format": format_type,
        "tone": tone,
        "impressions": impressions,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "score": score,
    }
