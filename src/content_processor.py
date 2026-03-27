"""
Content Processor - Uses Claude AI to transform raw news into:
  1. Engaging, dramatic video scripts
  2. Hindi narration text (Devanagari)
  3. Visual direction cues (colors, animations, overlays)
  4. Breaking news segments with hooks and cliffhangers

UPSC Mode adds:
  - GS paper tagging (GS1/GS2/GS3/GS4)
  - Syllabus topic tags
  - Prelims MCQ fact
  - Mains question angle
  - Key terms for quick revision
  - Exam relevance score (1-10)
  - Government scheme / static GK connection
"""

import os
import json
import re
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)

# ─── Visual styles ───────────────────────────────────────────────────────────
# Standard categories
CATEGORY_STYLES = {
    "World":                {"color": "#FF4136", "emoji": "🌍", "hindi": "विश्व समाचार"},
    "India":                {"color": "#FF851B", "emoji": "🇮🇳", "hindi": "भारत समाचार"},
    "Technology":           {"color": "#0074D9", "emoji": "💻", "hindi": "तकनीक"},
    "Science":              {"color": "#2ECC40", "emoji": "🔬", "hindi": "विज्ञान"},
    "Sports":               {"color": "#FFDC00", "emoji": "⚽", "hindi": "खेल"},
    "Business":             {"color": "#B10DC9", "emoji": "📈", "hindi": "व्यापार"},
    "Entertainment":        {"color": "#F012BE", "emoji": "🎬", "hindi": "मनोरंजन"},
    "Top Stories":          {"color": "#FF4136", "emoji": "⚡", "hindi": "मुख्य समाचार"},
    # UPSC-specific categories
    "Polity & Governance":  {"color": "#10B981", "emoji": "🏛️", "hindi": "राजनीति व शासन"},
    "Economy & Finance":    {"color": "#F59E0B", "emoji": "💰", "hindi": "अर्थव्यवस्था"},
    "Environment & Ecology":{"color": "#34D399", "emoji": "🌿", "hindi": "पर्यावरण"},
    "International Relations":{"color": "#6366F1", "emoji": "🤝", "hindi": "अंतरराष्ट्रीय"},
    "Science & Technology": {"color": "#0EA5E9", "emoji": "🚀", "hindi": "विज्ञान-तकनीक"},
    "History & Culture":    {"color": "#D97706", "emoji": "🏺", "hindi": "इतिहास व संस्कृति"},
    "Social Issues":        {"color": "#EC4899", "emoji": "👥", "hindi": "सामाजिक मुद्दे"},
    "Editorial":            {"color": "#8B5CF6", "emoji": "✍️", "hindi": "संपादकीय"},
    "default":              {"color": "#7FDBFF", "emoji": "📰", "hindi": "समाचार"},
}

# GS paper color scheme (for badge rendering)
GS_COLORS = {
    "GS1": "#8B5CF6",   # Purple  — History, Geography, Society, Culture
    "GS2": "#10B981",   # Green   — Polity, Governance, IR
    "GS3": "#3B82F6",   # Blue    — Economy, Science, Environment
    "GS4": "#F59E0B",   # Amber   — Ethics
    "GS1+GS2": "#6366F1",
    "GS2+GS3": "#0EA5E9",
}

# ─── Standard news prompt ────────────────────────────────────────────────────
STANDARD_SYSTEM_PROMPT = """You are a world-class Hindi news anchor and scriptwriter for a viral news channel.
Your job is to transform raw news articles into ELECTRIFYING, ENGAGING video scripts.

Rules:
1. Write in Hindi (Devanagari script) for narration
2. Use dramatic, punchy language — like breaking news
3. Add emotional hooks, rhetorical questions, suspense
4. Keep each news segment 15-25 seconds of speech (roughly 40-70 Hindi words)
5. Start with a POWERFUL opening hook in Hindi
6. Use simple, clear Hindi that everyone understands
7. Include transitional phrases between stories
8. Add dramatic pauses indicated by [रुकिए...]
9. Return ONLY valid JSON — no markdown, no extra text"""

STANDARD_NEWS_PROMPT = """Transform these {count} news articles into a Hindi TV news show script.

Articles:
{articles_json}

Return a JSON object with this EXACT structure:
{{
  "show_title": "आज की बड़ी खबरें",
  "show_title_english": "Today's Big News",
  "intro_hindi": "dramatic 2-sentence Hindi intro for the whole show",
  "outro_hindi": "powerful Hindi outro/sign-off",
  "segments": [
    {{
      "id": 1,
      "category": "category name",
      "category_hindi": "category in Hindi",
      "headline_hindi": "punchy Hindi headline (max 10 words)",
      "headline_english": "original English headline",
      "narration_hindi": "full Hindi narration 40-70 words, dramatic and engaging with [रुकिए...] pauses",
      "key_points_hindi": ["point 1 in Hindi", "point 2 in Hindi"],
      "impact_score": 1,
      "emotion": "shocking/inspiring/alarming/exciting/urgent",
      "visual_cue": "brief description of what to show visually",
      "lower_third": "short text for bottom of screen in Hindi",
      "breaking": true
    }}
  ],
  "ticker_items": ["short Hindi ticker text 1", "short Hindi ticker text 2"]
}}

Make it DRAMATIC. Make it VIRAL. This is prime time news!"""

# ─── UPSC mode prompts ───────────────────────────────────────────────────────
UPSC_SYSTEM_PROMPT = """You are an expert UPSC current-affairs educator AND a dramatic Hindi news anchor.
Your job is to transform news articles into HIGH-IMPACT Hindi video segments for IAS/IPS aspirants.

Your dual mandate:
1. DRAMATIC: Make each story engaging, emotional, and memorable — like breaking news TV
2. EDUCATIONAL: Tag every story with its UPSC exam relevance (GS paper, syllabus topics,
   prelims MCQ fact, mains angle, key terms)

Language rules:
- Write ALL narration in fluent Hindi (Devanagari script)
- Mix some English terms where commonly used in UPSC (e.g., "GDP", "Article 21", "UNFCCC")
- Use [रुकिए...] for dramatic pauses
- Keep narration 50-80 Hindi words per segment (20-30 seconds of speech)

Return ONLY valid JSON — no markdown, no extra text."""

UPSC_NEWS_PROMPT = """Transform these {count} news articles into a UPSC Current Affairs Hindi show script.

Articles:
{articles_json}

Return a JSON object with this EXACT structure:
{{
  "show_title": "UPSC करंट अफेयर्स — आज की बड़ी खबरें",
  "show_title_english": "UPSC Current Affairs Today",
  "intro_hindi": "dramatic 2-sentence Hindi intro mentioning UPSC exam relevance",
  "outro_hindi": "powerful sign-off reminding students to keep studying",
  "segments": [
    {{
      "id": 1,
      "category": "category name (e.g. Polity & Governance)",
      "category_hindi": "category in Hindi",
      "headline_hindi": "punchy Hindi headline max 10 words",
      "headline_english": "original English headline",
      "narration_hindi": "50-80 word Hindi narration, dramatic with [रुकिए...] pauses, weaves in why this matters for UPSC",
      "key_points_hindi": ["point 1 in Hindi", "point 2 in Hindi", "point 3 in Hindi"],
      "gs_paper": "GS2",
      "gs_paper_topic": "Indian Polity and Governance",
      "syllabus_tags": ["Parliament", "Constitutional Amendments", "Fundamental Rights"],
      "prelims_fact": "One punchy exam-ready fact in English (e.g. 'Article 370 was abrogated via Constitutional Order 272')",
      "mains_angle": "One crisp Mains question this story relates to (in English)",
      "key_terms": ["Term1", "Term2", "Term3"],
      "scheme_connection": "Name of related government scheme/committee/report if any (or null)",
      "static_gk_hook": "One interesting static GK fact connected to this story (in English)",
      "exam_relevance_score": 8,
      "impact_score": 8,
      "emotion": "shocking/inspiring/alarming/exciting/urgent",
      "visual_cue": "brief description of what to show visually",
      "lower_third": "short Hindi text for bottom of screen",
      "breaking": true
    }}
  ],
  "ticker_items": ["UPSC-relevant Hindi ticker text 1", "ticker text 2"],
  "daily_tip_hindi": "One quick Hindi study tip or motivational line for UPSC aspirants"
}}

GS paper guide:
- GS1: History, Culture, Geography, Society, World History
- GS2: Polity, Constitution, Governance, IR, Social Justice
- GS3: Economy, Agriculture, Science & Tech, Environment, Security
- GS4: Ethics, Integrity, Aptitude

Make it DRAMATIC for the video, PRECISE for the exam. This is the student's daily briefing!"""


class ContentProcessor:
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-opus-4-6"

    def process_news(self, articles: list[dict], upsc_mode: bool = False) -> dict:
        """
        Transform raw news articles into an engaging Hindi video script.

        Args:
            articles: List of news article dicts
            upsc_mode: When True, adds GS tags, MCQ facts, mains angles,
                       key terms, and exam relevance scores to every segment.

        Returns structured show data with segments, narration, visual cues,
        and (in UPSC mode) full exam metadata.
        """
        if not articles:
            raise ValueError("No articles provided")

        simplified = []
        for i, a in enumerate(articles, 1):
            simplified.append(
                {
                    "id": i,
                    "category": a.get("category", "World"),
                    "title": a.get("title", ""),
                    "description": a.get("description", "")[:300],
                    "source": a.get("source", ""),
                }
            )

        if upsc_mode:
            system_prompt = UPSC_SYSTEM_PROMPT
            user_prompt = UPSC_NEWS_PROMPT.format(
                count=len(simplified),
                articles_json=json.dumps(simplified, ensure_ascii=False, indent=2),
            )
            max_tokens = 10000
        else:
            system_prompt = STANDARD_SYSTEM_PROMPT
            user_prompt = STANDARD_NEWS_PROMPT.format(
                count=len(simplified),
                articles_json=json.dumps(simplified, ensure_ascii=False, indent=2),
            )
            max_tokens = 8000

        logger.info(
            f"Sending {len(simplified)} articles to Claude "
            f"({'UPSC mode' if upsc_mode else 'standard mode'})..."
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text.strip()
        logger.info(f"Claude response received ({len(raw_text)} chars)")

        show_data = self._parse_response(raw_text)
        show_data = self._enrich_with_styles(show_data, upsc_mode=upsc_mode)
        show_data["upsc_mode"] = upsc_mode

        return show_data

    def _parse_response(self, raw_text: str) -> dict:
        """Parse Claude's JSON response with fallback handling."""
        if "```json" in raw_text:
            raw_text = re.sub(r"```json\s*", "", raw_text)
            raw_text = re.sub(r"```\s*$", "", raw_text)
        elif "```" in raw_text:
            raw_text = re.sub(r"```\w*\s*", "", raw_text)

        raw_text = raw_text.strip()

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse Claude response as JSON: {e}")

    def _enrich_with_styles(self, show_data: dict, upsc_mode: bool = False) -> dict:
        """Add visual styles to each segment based on category."""
        segments = show_data.get("segments", [])
        for segment in segments:
            cat = segment.get("category", "default")
            style = CATEGORY_STYLES.get(cat, CATEGORY_STYLES["default"])
            segment["color"] = style["color"]
            segment["emoji"] = style["emoji"]
            if not segment.get("category_hindi"):
                segment["category_hindi"] = style["hindi"]

            # Add GS color if in UPSC mode
            if upsc_mode:
                gs = segment.get("gs_paper", "GS2")
                segment["gs_color"] = GS_COLORS.get(gs, "#6366F1")

        # Sort by exam_relevance_score (UPSC) or impact_score (standard)
        sort_key = "exam_relevance_score" if upsc_mode else "impact_score"
        segments.sort(key=lambda x: x.get(sort_key, x.get("impact_score", 5)), reverse=True)

        # Tag top segments as breaking
        for seg in segments[:3]:
            score = seg.get("exam_relevance_score", seg.get("impact_score", 0))
            if score >= 7:
                seg["breaking"] = True

        show_data["segments"] = segments
        return show_data

    def generate_show_intro(self, show_data: dict) -> str:
        date_str = _get_hindi_date()
        intro = show_data.get("intro_hindi", "")
        if not intro:
            if show_data.get("upsc_mode"):
                intro = "आज के करंट अफेयर्स जो हर UPSC aspirant को जानने चाहिए।"
            else:
                intro = "आज की सबसे बड़ी खबरें लेकर हम आ गए हैं।"
        return f"नमस्कार! {date_str} की मुख्य खबरें। {intro}"

    def generate_show_outro(self, show_data: dict) -> str:
        outro = show_data.get("outro_hindi", "")
        if not outro:
            if show_data.get("upsc_mode"):
                outro = "यह थे आज के UPSC करंट अफेयर्स। पढ़ते रहो, आगे बढ़ते रहो।"
            else:
                outro = "यह थीं आज की प्रमुख खबरें। जुड़े रहिए हमारे साथ।"
        return outro + " धन्यवाद!"


def _get_hindi_date() -> str:
    """Return today's date in Hindi format."""
    from datetime import datetime

    now = datetime.now()
    months_hindi = [
        "जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून",
        "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर",
    ]
    days_hindi = [
        "सोमवार", "मंगलवार", "बुधवार", "गुरुवार",
        "शुक्रवार", "शनिवार", "रविवार",
    ]
    day_name = days_hindi[now.weekday()]
    month_name = months_hindi[now.month - 1]
    return f"{day_name}, {now.day} {month_name} {now.year}"
