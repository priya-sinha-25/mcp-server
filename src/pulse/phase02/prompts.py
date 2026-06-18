"""System and user prompt templates for Stage A and Stage B (DEC-011)."""

from __future__ import annotations

import json

from pulse.models import NormalizedReview, ThemeCluster

# ---------------------------------------------------------------------------
# Stage A — Theme discovery
# ---------------------------------------------------------------------------

STAGE_A_SYSTEM = """\
You are a product analyst extracting themes from mobile app reviews.

Your task:
- Analyse the provided reviews and identify the most important recurring themes.
- Return ONLY a valid JSON object with a single key "themes" containing an array.
- Each theme object must have exactly these keys:
    "theme_id"    : a short slug like "theme_1", "theme_2", etc.
    "label"       : a concise noun phrase (3–6 words) naming the theme
    "description" : one sentence explaining what users say about this theme
    "review_ids"  : array of review_id strings from the input that support this theme

Rules:
- Return AT MOST {max_themes} themes.
- Every review_id in "review_ids" must appear exactly as given in the input.
- Do not invent review_ids.
- Do not include any text outside the JSON object.
"""

STAGE_A_USER = """\
Here are {n} app reviews. Each line is a JSON object with fields:
review_id, rating (1–5), review_date, body.

Reviews:
{reviews_json}

Identify up to {max_themes} distinct themes. Return JSON only.
"""


def build_stage_a_messages(
    reviews: list[NormalizedReview],
    max_themes: int = 5,
) -> list[dict[str, str]]:
    """Build the messages list for the Stage A Groq call."""
    review_lines = [
        json.dumps(
            {
                "review_id": r.review_id,
                "rating": r.rating,
                "review_date": r.review_date.isoformat(),
                "body": r.body,
            },
            ensure_ascii=False,
        )
        for r in reviews
    ]
    reviews_json = "\n".join(review_lines)
    return [
        {
            "role": "system",
            "content": STAGE_A_SYSTEM.format(max_themes=max_themes),
        },
        {
            "role": "user",
            "content": STAGE_A_USER.format(
                n=len(reviews),
                reviews_json=reviews_json,
                max_themes=max_themes,
            ),
        },
    ]


# ---------------------------------------------------------------------------
# Stage B — Pulse drafting
# ---------------------------------------------------------------------------

STAGE_B_SYSTEM = """\
You are a product analyst writing a concise weekly pulse for stakeholders.

Your task:
- Use the provided themes and supporting reviews to draft a WeeklyPulse.
- Return ONLY a valid JSON object with these exact keys:
    "week_label"  : the week string provided (e.g. "2026-W18")
    "headline"    : one sentence executive framing (≤20 words)
    "top_themes"  : array of exactly 3 theme objects (pick the 3 most important)
                    each with: "theme_id", "label", "description", "review_ids"
    "quotes"      : array of exactly 3 verbatim strings copied word-for-word
                    from the review bodies provided
    "actions"     : array of exactly 3 short, actionable improvement ideas

Rules:
- The entire pulse body (headline + themes descriptions + quotes + actions) \
must be ≤ 250 words.
- Every quote must be an exact substring of one of the review bodies provided.
- Do not add, paraphrase, or truncate quotes.
- top_themes must contain exactly 3 items.
- quotes must contain exactly 3 items.
- actions must contain exactly 3 items.
- Do not include any text outside the JSON object.
"""

STAGE_B_REPAIR_SUFFIX = """

The previous response was rejected for these reasons:
{reasons}

Fix exactly those issues and return the corrected JSON object only.
"""

STAGE_B_USER = """\
Week: {week_label}

Discovered themes (JSON):
{themes_json}

Supporting review bodies (for quote selection):
{evidence_json}

Draft the WeeklyPulse. Return JSON only.
"""


def build_stage_b_messages(
    clusters: list[ThemeCluster],
    evidence: list[NormalizedReview],
    week_label: str,
    repair_reasons: list[str] | None = None,
) -> list[dict[str, str]]:
    """Build the messages list for the Stage B Groq call."""
    themes_json = json.dumps(
        [c.to_dict() for c in clusters], indent=2, ensure_ascii=False
    )
    evidence_json = json.dumps(
        [{"review_id": r.review_id, "body": r.body} for r in evidence],
        indent=2,
        ensure_ascii=False,
    )
    user_content = STAGE_B_USER.format(
        week_label=week_label,
        themes_json=themes_json,
        evidence_json=evidence_json,
    )
    if repair_reasons:
        user_content += STAGE_B_REPAIR_SUFFIX.format(
            reasons="\n".join(f"- {r}" for r in repair_reasons)
        )
    return [
        {"role": "system", "content": STAGE_B_SYSTEM},
        {"role": "user", "content": user_content},
    ]
