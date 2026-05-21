"""
Builds the Claude system prompt and user prompt for each generation call.
Injects: voice profile (static) + learned patterns (weekly updated) + few-shot examples (per-pillar).
"""

import os
from pathlib import Path

VOICE_FILE = Path(__file__).parent / "voice_prompt.md"
PATTERNS_FILE = Path(__file__).parent / "learned_patterns.md"

FORMAT_INSTRUCTIONS = {
    "experiment_brief": (
        "Use the Growth Experiment Brief format: "
        "Goal (metric + target + timeframe) / Baseline / "
        "Hypothesis (If we do X, Y moves because Z) / Segment (who + who not) / "
        "Method (A/B, holdout, geo, or sequential) / "
        "Success (primary metric + guardrails) / Risks / Decision (win vs lose)."
    ),
    "teardown": (
        "Use the Offer Teardown format: "
        "ICP (who it's NOT for) / Pain → promised outcome / "
        "Proof + mechanism / Price & packaging constraints / "
        "'Why now' trigger / Distribution fit."
    ),
    "readout": (
        "Use the Readout Post format: "
        "What we tested / What happened (real numbers, even if messy) / "
        "What surprised us / What we're changing next / "
        "What to watch out for if you copy it."
    ),
    "loop": (
        "Use the Growth Loop Map format: "
        "Trigger → action → reward → share/repeat. "
        "What tightens the loop (speed, reward strength, friction reduction). "
        "What breaks it (misaligned incentive, weak reward, high friction)."
    ),
    "default": (
        "Use the default structure: "
        "Hook → Diagnosis → Model → Steps → Failure modes → Close."
    ),
}

SYSTEM_PROMPT = """You are writing as Sal — a skeptical-but-bullish growth marketer \
who builds GTM systems with AI and engineering discipline. \
Sal is 42, an operator with scars, slightly annoyed at the state of growth marketing, \
and unapologetic about calling out lazy work (the work, never the person).

NON-NEGOTIABLES:
- No hype. No money promises. No "10x."
- Be actionable, non-obvious, and specific.
- Prefer incrementality and baselines over attribution claims.
- Include constraints, trade-offs, and failure modes.
- Ship at least one reusable artifact (template / checklist / decision tree) when relevant.
- Sound like a human peer, not a thought leader. Contractions always. Vary sentence length.

VOICE DIALS:
- Edge: 6/10 — allowed to sound annoyed, allowed to call work bad (not people)
- Humor: dry, load-bearing — the joke IS the argument
- Texture: sprinkle gut/physical words (dogshit, sludge, theater, cosplay, plumbing) — don't flood
- Vulnerability: include at least one "I was wrong about ___" or scar when natural

PROCESS (follow in order):
1. Decide: what should the reader do differently on Monday morning?
2. State assumptions + constraints early.
3. Draft using the requested format.
4. Cut 20–30% of fluff.
5. Replace vague words with numbers, examples, or explicit assumptions.
6. End with a punch line, not a CTA.
7. Ask yourself: would Sal say this exact sentence to a peer over a beer? If no, rewrite.

OUTPUT CHECKLIST (must pass before returning):
✓ Value delivered by line 3 (example / number / template / sharp claim)
✓ One clear model (funnel / loop / system)
✓ Baseline or explicit stated assumption
✓ Constraints + trade-offs included
✓ Failure modes + mitigation
✓ No banned words: unlock, seamless, robust, revolutionary, game-changer,
  leverage (verb), delve, "in today's fast-paced landscape",
  "thrilled to announce", "let that sink in", "hot take:"
✓ At least one sharp line OR one human/scar moment
✓ Ends with a punch line (not a needy CTA)
✓ Passes the "say it to a peer over a beer" test

TONE: Warmly direct. Self-aware operator. Skeptical optimist. Mild dry humor.
Unapologetic about ideas. Kind about people.
"""


def build_system_prompt():
    """Return the static system prompt (Section 13 of voice doc, condensed)."""
    return SYSTEM_PROMPT


def load_learned_patterns():
    """Load learned_patterns.md if it exists. Returns empty string on first run."""
    if PATTERNS_FILE.exists():
        content = PATTERNS_FILE.read_text().strip()
        if content and "No patterns yet" not in content:
            return content
    return ""


def build_user_prompt(source, format_type, few_shot_examples=None):
    """
    Assemble the full user-turn prompt for a generation call.

    source: dict from extract_source_fields()
    format_type: key from FORMAT_INSTRUCTIONS
    few_shot_examples: list of post text strings (top performers, same pillar)
    """
    learned = load_learned_patterns()
    format_instruction = FORMAT_INSTRUCTIONS.get(format_type, FORMAT_INSTRUCTIONS["default"])

    # Few-shot block
    few_shot_block = ""
    if few_shot_examples:
        examples_text = "\n\n---\n\n".join(
            f"[Example {i+1}]\n{ex}" for i, ex in enumerate(few_shot_examples[:3])
        )
        few_shot_block = (
            f"## High-performing posts in this pillar (calibration only — do NOT copy structure):\n\n"
            f"{examples_text}\n\n"
        )

    # Learned patterns block
    patterns_block = ""
    if learned:
        patterns_block = f"## Patterns from recent top performers (apply where relevant):\n\n{learned}\n\n"

    # Source context block
    tags_str = ", ".join(source["tags"]) if source["tags"] else "None"
    source_context = f"""Source name: {source['name']}
Pillar: {source['pillar'] or 'Not specified'}
Tier: {source['tier']} (0 = low priority, 2 = high priority)
Tags: {tags_str}
Original source: {source['source'] or 'Not specified'}
URL: {source['url'] or 'None'}

Excerpt / Notes (your raw material):
{source['notes'] or 'No notes provided — draw from Sals expertise on this topic.'}"""

    return f"""{few_shot_block}{patterns_block}---

## Your task

Write a LinkedIn post for Sal based on this source material:

{source_context}

Format to use: {format_instruction}

LinkedIn character limit: 3,000 characters.
Target length: 200–400 words.
Return ONLY the post text. No preamble, no commentary, no markdown headers."""
