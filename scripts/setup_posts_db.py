"""
setup_posts_db.py — One-time setup script.

Creates the LinkedIn Posts database in your Notion workspace and prints
the database ID you need to add to your .env file.

Run ONCE before your first generate.py run:
  python scripts/setup_posts_db.py

You'll be prompted for the Notion page ID of the parent page where
the database should live (e.g. your Marketing workspace page).

Get a page ID from any Notion page URL:
  https://www.notion.so/yourworkspace/My-Page-<PAGE_ID_IS_HERE>
"""

import os
import sys
import requests

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


def get_headers():
    key = os.environ.get("NOTION_API_KEY")
    if not key:
        print("❌ NOTION_API_KEY not set. Export it first:")
        print("   export NOTION_API_KEY=secret_xxxx")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def create_posts_db(parent_page_id: str) -> str:
    """Create the LinkedIn Posts DB under parent_page_id. Returns new DB id."""
    url = f"{BASE_URL}/databases"
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "📝 LinkedIn Posts"}}],
        "properties": {
            # Core
            "Name": {"title": {}},
            "Generated Post": {"rich_text": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Draft Ready", "color": "blue"},
                        {"name": "Approved", "color": "green"},
                        {"name": "Posted", "color": "gray"},
                    ]
                }
            },
            "Post Date": {"date": {}},

            # Content metadata
            "Pillar": {
                "select": {
                    "options": [
                        {"name": "Growth Systems", "color": "brown"},
                        {"name": "Monetization", "color": "gray"},
                        {"name": "Retention", "color": "red"},
                        {"name": "Acquisition", "color": "blue"},
                        {"name": "Activation", "color": "green"},
                        {"name": "Strategy", "color": "purple"},
                    ]
                }
            },
            "Format": {
                "select": {
                    "options": [
                        {"name": "default", "color": "gray"},
                        {"name": "experiment_brief", "color": "blue"},
                        {"name": "teardown", "color": "orange"},
                        {"name": "readout", "color": "green"},
                        {"name": "loop", "color": "purple"},
                    ]
                }
            },
            "Tone": {
                "select": {
                    "options": [
                        {"name": "Thought leadership", "color": "blue"},
                        {"name": "Provocative", "color": "red"},
                        {"name": "Data-driven", "color": "green"},
                        {"name": "Story", "color": "orange"},
                        {"name": "Artifact", "color": "purple"},
                    ]
                }
            },

            # Engagement (populated by sync_engagement.py)
            "Impressions": {"number": {"format": "number"}},
            "Likes": {"number": {"format": "number"}},
            "Comments": {"number": {"format": "number"}},
            "Shares": {"number": {"format": "number"}},
            "Engagement Score": {"number": {"format": "number"}},
            "Top Performer": {"checkbox": {}},

            # Optional: qualitative notes
            "What Worked": {"rich_text": {}},

            # Traceability back to Source Inbox
            "Source Name": {"rich_text": {}},
            "Source Pillar": {"rich_text": {}},
        },
    }

    res = requests.post(url, headers=get_headers(), json=payload)

    if res.status_code != 200:
        print(f"❌ Notion API error {res.status_code}:")
        print(res.text)
        sys.exit(1)

    data = res.json()
    db_id = data["id"].replace("-", "")
    db_url = data.get("url", "")
    return db_id, db_url


def main():
    print("=" * 60)
    print("  LinkedIn Posts DB — One-Time Setup")
    print("=" * 60)
    print()
    print("This creates the LinkedIn Posts database in Notion.")
    print("You only need to run this once.\n")
    print("Find your parent page ID from a Notion URL, e.g.:")
    print("  https://notion.so/yourworkspace/MyPage-<ID HERE>")
    print()

    parent_id = input("Enter the parent Notion page ID: ").strip()

    # Strip dashes if user pasted a UUID
    parent_id = parent_id.replace("-", "")

    if len(parent_id) != 32:
        print(f"⚠️  That doesn't look like a valid Notion page ID (got {len(parent_id)} chars).")
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != "y":
            sys.exit(1)

    print("\nCreating LinkedIn Posts DB in Notion...")
    db_id, db_url = create_posts_db(parent_id)

    print(f"\n✅ Database created successfully!")
    print(f"   URL: {db_url}")
    print()
    print("=" * 60)
    print("  Add this to your .env file (and GitHub Secrets):")
    print("=" * 60)
    print(f"  NOTION_POSTS_DB_ID={db_id}")
    print()
    print("Don't forget to share the new database with your Notion integration!")
    print("Notion → Database → ••• → Connections → Add connection → your integration")


if __name__ == "__main__":
    main()
