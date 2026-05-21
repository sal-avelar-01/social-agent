"""
generate.py — Daily LinkedIn post generator.

Reads up to POSTS_PER_RUN items from the Source Inbox (Status = New, sorted by Tier desc),
generates a LinkedIn post for each using Claude, writes drafts to the LinkedIn Posts DB,
and marks the source item as Used.

Run:   python agent/generate.py
Env:   NOTION_API_KEY, NOTION_SOURCE_DB_ID, NOTION_POSTS_DB_ID, ANTHROPIC_API_KEY
       POSTS_PER_RUN (optional, default 3)
       POST_FORMAT (optional: default | experiment_brief | teardown | readout | loop)
"""

import os
import sys
import anthropic

# Resolve import path regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.notion_client import NotionClient, extract_source_fields, extract_post_fields
from prompts.system_prompt import build_system_prompt, build_user_prompt

POSTS_PER_RUN = int(os.environ.get("POSTS_PER_RUN", "3"))
DEFAULT_FORMAT = os.environ.get("POST_FORMAT", "default")
DEFAULT_TONE = os.environ.get("POST_TONE", "Thought leadership")


def get_few_shot_examples(notion: NotionClient, pillar: str) -> list[str]:
    """Pull up to 3 top-performing posts from the same pillar as few-shot examples."""
    if not pillar:
        return []
    try:
        pages = notion.get_top_performers_by_pillar(pillar, limit=3)
        examples = []
        for p in pages:
            fields = extract_post_fields(p)
            if fields["post"]:
                examples.append(f"[Score: {fields['score']} | Format: {fields['format']}]\n{fields['post']}")
        return examples
    except Exception as e:
        print(f"  ⚠️  Could not fetch few-shot examples: {e}")
        return []


def generate_post(source: dict, format_type: str, tone: str,
                  few_shot_examples: list[str]) -> str:
    """Call Claude to generate a LinkedIn post from a source item."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system = build_system_prompt()
    user = build_user_prompt(source, format_type, few_shot_examples)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text.strip()


def run():
    print(f"🚀 LinkedIn Post Generator — pulling up to {POSTS_PER_RUN} sources\n")

    notion = NotionClient()

    sources = notion.get_new_sources(limit=POSTS_PER_RUN)
    if not sources:
        print("📭 No new sources found in Source Inbox. Add items with Status = New.")
        return

    print(f"📋 Found {len(sources)} source(s) to process\n")

    for i, page in enumerate(sources, 1):
        source = extract_source_fields(page)
        format_type = DEFAULT_FORMAT
        tone = DEFAULT_TONE

        print(f"[{i}/{len(sources)}] Generating post for: {source['name']}")
        print(f"        Pillar: {source['pillar'] or 'None'} | Tier: {source['tier']} | Format: {format_type}")

        # Fetch few-shot examples from same pillar
        examples = get_few_shot_examples(notion, source["pillar"])
        if examples:
            print(f"        📎 Injecting {len(examples)} few-shot example(s)")

        try:
            post_text = generate_post(source, format_type, tone, examples)
            print(f"        ✅ Post generated ({len(post_text)} chars)")

            # Write draft to LinkedIn Posts DB
            notion.create_post(
                name=source["name"],
                generated_post=post_text,
                pillar=source["pillar"],
                format_type=format_type,
                tone=tone,
                source_name=source["name"],
                source_pillar=source["pillar"],
            )
            print(f"        📝 Draft written to LinkedIn Posts DB")

            # Mark source as Used
            notion.mark_source_used(source["id"])
            print(f"        🔖 Source marked as Used\n")

        except Exception as e:
            print(f"        ❌ Error processing '{source['name']}': {e}\n")
            continue

    print("✅ Generation run complete.")


if __name__ == "__main__":
    run()
