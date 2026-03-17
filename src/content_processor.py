"""
Content Processor - Uses Claude AI to transform raw news into:
  1. Engaging, dramatic video scripts
  2. Hindi narration text (Devanagari)
  3. Visual direction cues (colors, animations, overlays)
  4. Breaking news segments with hooks and cliffhangers
"""

import os
import json
import re
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)

# Emotion/category to visual style mapping
CATEGORY_STYLES = {
    "World":       {"color": "#FF4136", "emoji": "🌍", "hindi": "विश्व समाचार"},
    "India":       {"color": "#FF851B", "emoji": "🇮🇳", "hindi": "भारत समाचार"},
    "Technology":  {"color": "#0074D9", "emoji": "💻", "hindi": "तकनीक"},
    "Science":     {"color": "#2ECC40", "emoji": "🔬", "hindi": "विज्ञान"},
    "Sports":      {"color": "#FFDC00", "emoji": "⚽", "hindi": "खेल"},
    "Business":    {"color": "#B10DC9", "emoji": "📈", "hindi": "व्यापार"},
    "Entertainment": {"color": "#F012BE", "emoji": "🎬", "hindi": "मनोरंजन"},
    "Top Stories": {"color": "#FF4136", "emoji": "⚡", "hindi": "मुख्य समाचार"},
    "default":     {"color": "#7FDBFF", "emoji": "📰", "hindi": "समाचार"},
}

SYSTEM_PROMPT = """You are a world-class Hindi news anchor and scriptwriter for a viral news channel.
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

NEWS_SCRIPT_PROMPT = """Transform these {count} news articles into a Hindi TV news show script.

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
      "impact_score": 1-10,
      "emotion": "shocking/inspiring/alarming/exciting/urgent",
      "visual_cue": "brief description of what to show visually",
      "lower_third": "short text for bottom of screen in Hindi",
      "breaking": true/false
    }}
  ],
  "ticker_items": ["short Hindi ticker text 1", "short Hindi ticker text 2", ...]
}}

Make it DRAMATIC. Make it VIRAL. This is prime time news!"""


class ContentProcessor:
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-opus-4-6"

    def process_news(self, articles: list[dict]) -> dict:
        """
        Transform raw news articles into an engaging Hindi video script.
        Returns structured show data with segments, narration, visual cues.
        """
        if not articles:
            raise ValueError("No articles provided")

        # Prepare simplified article data for prompt
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

        prompt = NEWS_SCRIPT_PROMPT.format(
            count=len(simplified),
            articles_json=json.dumps(simplified, ensure_ascii=False, indent=2),
        )

        logger.info(f"Sending {len(simplified)} articles to Claude for processing...")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = response.content[0].text.strip()
        logger.info(f"Claude response received ({len(raw_text)} chars)")

        # Parse JSON response
        show_data = self._parse_response(raw_text)

        # Enrich segments with visual styles
        show_data = self._enrich_with_styles(show_data)

        return show_data

    def _parse_response(self, raw_text: str) -> dict:
        """Parse Claude's JSON response with fallback handling."""
        # Strip markdown code fences if present
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
            logger.debug(f"Raw text (first 500): {raw_text[:500]}")
            # Try to extract JSON object
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse Claude response as JSON: {e}")

    def _enrich_with_styles(self, show_data: dict) -> dict:
        """Add visual styles to each segment based on category."""
        segments = show_data.get("segments", [])
        for segment in segments:
            cat = segment.get("category", "default")
            style = CATEGORY_STYLES.get(cat, CATEGORY_STYLES["default"])
            segment["color"] = style["color"]
            segment["emoji"] = style["emoji"]
            if not segment.get("category_hindi"):
                segment["category_hindi"] = style["hindi"]

        # Sort by impact score (highest first)
        segments.sort(key=lambda x: x.get("impact_score", 5), reverse=True)

        # Tag top 3 as breaking news if not already
        for i, seg in enumerate(segments[:3]):
            if seg.get("impact_score", 0) >= 7:
                seg["breaking"] = True

        show_data["segments"] = segments
        return show_data

    def generate_show_intro(self, show_data: dict) -> str:
        """Generate a dramatic show intro narration."""
        date_str = _get_hindi_date()
        intro = show_data.get("intro_hindi", "")
        if not intro:
            intro = f"आज की सबसे बड़ी खबरें लेकर हम आ गए हैं।"
        return f"नमस्कार! {date_str} की मुख्य खबरें। {intro}"

    def generate_show_outro(self, show_data: dict) -> str:
        """Generate show outro."""
        outro = show_data.get("outro_hindi", "")
        if not outro:
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test with sample articles
    sample_articles = [
        {
            "title": "India launches new space mission to Moon",
            "description": "ISRO successfully launched Chandrayaan-4 with new rover technology",
            "category": "Science",
            "source": "ISRO",
        },
        {
            "title": "Global AI regulation summit begins in Geneva",
            "description": "World leaders gather to discuss AI safety and governance frameworks",
            "category": "Technology",
            "source": "Reuters",
        },
        {
            "title": "India vs Australia cricket final: Match begins today",
            "description": "The two teams face off in the World Cup final in Mumbai",
            "category": "Sports",
            "source": "BBC Sports",
        },
    ]

    processor = ContentProcessor()
    show_data = processor.process_news(sample_articles)
    print(json.dumps(show_data, ensure_ascii=False, indent=2))
