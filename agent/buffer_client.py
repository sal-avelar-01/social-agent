"""
buffer_client.py — Buffer API integration.

Two jobs:
  1. sync_analytics()  — pull sent post stats from Buffer → update Notion Posts DB
  2. push_to_buffer()  — push an approved Notion draft → Buffer as a scheduled post

Buffer API docs: https://buffer.com/developers/api
Get your access token: https://buffer.com/developers/apps

Env vars needed:
  BUFFER_ACCESS_TOKEN   — your personal access token
  BUFFER_PROFILE_ID     — your LinkedIn profile ID in Buffer (see get_profiles())
"""

import os
import requests
from datetime import datetime

BUFFER_BASE = "https://api.bufferapp.com/1"


class BufferClient:
    def __init__(self):
        self.token = os.environ.get("BUFFER_ACCESS_TOKEN")
        if not self.token:
            raise EnvironmentError(
                "BUFFER_ACCESS_TOKEN not set. "
                "Get yours at https://buffer.com/developers/apps"
            )
        self.profile_id = os.environ.get("BUFFER_PROFILE_ID")
        self.params = {"access_token": self.token}

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_profiles(self):
        """
        List all connected Buffer profiles.
        Run this once to find your BUFFER_PROFILE_ID.

        Usage: python -c "from agent.buffer_client import BufferClient; BufferClient().print_profiles()"
        """
        res = requests.get(f"{BUFFER_BASE}/profiles.json", params=self.params)
        res.raise_for_status()
        return res.json()

    def print_profiles(self):
        """Helper: print profile IDs and names. Run once during setup."""
        profiles = self.get_profiles()
        print("\nYour Buffer profiles:\n")
        for p in profiles:
            print(f"  ID:       {p['id']}")
            print(f"  Service:  {p['service']} ({p.get('service_type', '')})")
            print(f"  Name:     {p.get('formatted_username', '')}")
            print()
        print("Set BUFFER_PROFILE_ID to the ID of your LinkedIn profile above.")

    # ------------------------------------------------------------------
    # Analytics sync
    # ------------------------------------------------------------------

    def get_sent_updates(self, count=50, page=1):
        """
        Fetch sent (published) posts with their engagement stats.
        Buffer returns stats: reach, clicks, favorites, mentions, shares, comments.

        count: max 100 per page
        """
        if not self.profile_id:
            raise EnvironmentError(
                "BUFFER_PROFILE_ID not set. Run print_profiles() to find it."
            )
        params = {
            **self.params,
            "count": count,
            "page": page,
        }
        res = requests.get(
            f"{BUFFER_BASE}/profiles/{self.profile_id}/updates/sent.json",
            params=params,
        )
        res.raise_for_status()
        return res.json()

    def get_all_sent_updates(self, max_pages=5):
        """Paginate through sent updates. Returns a flat list of update dicts."""
        all_updates = []
        for page in range(1, max_pages + 1):
            data = self.get_sent_updates(count=100, page=page)
            updates = data.get("updates", [])
            if not updates:
                break
            all_updates.extend(updates)
            if not data.get("total", 0) > len(all_updates):
                break
        return all_updates

    def extract_stats(self, update: dict) -> dict:
        """
        Parse a Buffer update into the stats dict used by Notion.
        Buffer field → our field mapping:
          reach/impressions → impressions
          favorites         → likes (LinkedIn reactions)
          comments          → comments
          shares            → shares
        """
        stats = update.get("statistics", {})
        text = update.get("text", "")
        # Truncate to first ~80 chars for matching against Notion Name
        preview = text[:80].strip()

        return {
            "buffer_id": update.get("id", ""),
            "text_preview": preview,
            "sent_at": update.get("sent_at"),  # Unix timestamp
            "impressions": stats.get("reach", 0) or 0,
            "likes": stats.get("favorites", 0) or 0,
            "comments": stats.get("comments", 0) or 0,
            "shares": stats.get("shares", 0) or 0,
        }

    # ------------------------------------------------------------------
    # Push to Buffer
    # ------------------------------------------------------------------

    def create_draft(self, post_text: str, scheduled_at: int = None) -> dict:
        """
        Push a post to Buffer as a draft (or scheduled post).

        post_text:    the LinkedIn post content
        scheduled_at: Unix timestamp. If None, adds to queue (recommended).

        Returns the Buffer update object.
        """
        if not self.profile_id:
            raise EnvironmentError("BUFFER_PROFILE_ID not set.")

        payload = {
            "access_token": self.token,
            "profile_ids[]": self.profile_id,
            "text": post_text,
        }
        if scheduled_at:
            payload["scheduled_at"] = scheduled_at
        else:
            # Add to end of queue instead of scheduling
            payload["now"] = "false"
            payload["top"] = "false"

        res = requests.post(f"{BUFFER_BASE}/updates/create.json", data=payload)
        res.raise_for_status()
        return res.json()


# ------------------------------------------------------------------
# Standalone runner: print profiles (setup helper)
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    client = BufferClient()
    if len(sys.argv) > 1 and sys.argv[1] == "profiles":
        client.print_profiles()
    else:
        print("Usage:")
        print("  python agent/buffer_client.py profiles   # list your Buffer profile IDs")
