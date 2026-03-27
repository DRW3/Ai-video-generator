"""
TTS Generator - Converts Hindi text to speech audio files
Uses gTTS (Google Text-to-Speech) for natural Hindi narration.
Supports:
  - Slow/fast mode
  - Audio stitching with pauses
  - Per-segment audio files
  - Show intro/outro audio
"""

import os
import re
import time
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TTSGenerator:
    def __init__(self, output_dir: str = "output/audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._test_gtts()

    def _test_gtts(self):
        """Verify gTTS is available."""
        try:
            from gtts import gTTS
            self._gtts_class = gTTS
            logger.info("gTTS initialized successfully")
        except ImportError:
            raise ImportError("gTTS not installed. Run: pip install gTTS")

    def text_to_speech(
        self,
        text: str,
        filename: str,
        lang: str = "hi",
        slow: bool = False,
        retries: int = 3,
    ) -> Optional[Path]:
        """
        Convert text to speech and save as MP3.

        Args:
            text: Hindi text to convert
            filename: Output filename (without extension)
            lang: Language code (default 'hi' for Hindi)
            slow: Use slower speech rate
            retries: Number of retry attempts

        Returns:
            Path to generated MP3 file, or None if failed
        """
        # Clean text for TTS
        clean_text = self._clean_for_tts(text)
        if not clean_text:
            logger.warning(f"Empty text for {filename}")
            return None

        output_path = self.output_dir / f"{filename}.mp3"

        for attempt in range(retries):
            try:
                tts = self._gtts_class(text=clean_text, lang=lang, slow=slow)
                tts.save(str(output_path))
                logger.info(f"Generated TTS: {output_path} ({len(clean_text)} chars)")
                return output_path

            except Exception as e:
                logger.warning(f"TTS attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)

        logger.error(f"TTS failed after {retries} attempts for: {filename}")
        return None

    def generate_segment_audio(
        self, segment: dict, segment_id: int
    ) -> Optional[Path]:
        """Generate audio for a single news segment."""
        narration = segment.get("narration_hindi", "")
        if not narration:
            logger.warning(f"No narration for segment {segment_id}")
            return None

        # Add dramatic pauses and emphasis
        enhanced = self._enhance_narration(narration, segment)
        filename = f"segment_{segment_id:02d}"
        return self.text_to_speech(enhanced, filename)

    def generate_show_audio(self, show_data: dict) -> dict:
        """
        Generate all audio files for a complete news show.

        Returns:
            dict mapping audio type to file paths
        """
        audio_files = {}
        segments = show_data.get("segments", [])

        # Show intro
        logger.info("Generating show intro audio...")
        intro_text = show_data.get("intro_hindi", "आज की बड़ी खबरें!")
        date_text = _get_hindi_date_text()
        full_intro = f"नमस्कार दोस्तों! {date_text}। {intro_text}"
        path = self.text_to_speech(full_intro, "intro", slow=False)
        if path:
            audio_files["intro"] = str(path)

        # Welcome jingle text
        upsc_mode = show_data.get("upsc_mode", False)
        if upsc_mode:
            welcome_text = (
                "नमस्कार UPSC aspirants! आज के करंट अफेयर्स जो "
                "Prelims और Mains दोनों के लिए ज़रूरी हैं।"
            )
        else:
            welcome_text = (
                "आइए जानते हैं आज की सबसे बड़ी और महत्वपूर्ण खबरें। "
                "यह हैं हमारी टॉप स्टोरीज।"
            )
        path = self.text_to_speech(welcome_text, "welcome", slow=False)
        if path:
            audio_files["welcome"] = str(path)

        # Each segment
        for i, segment in enumerate(segments, 1):
            logger.info(f"Generating audio for segment {i}/{len(segments)}...")

            # Category / GS paper announcement
            cat_hindi = segment.get("category_hindi", "समाचार")
            breaking = segment.get("breaking", False)
            gs_paper = segment.get("gs_paper", "")

            if upsc_mode and gs_paper:
                if breaking:
                    announcement = f"ब्रेकिंग! {gs_paper} — {cat_hindi} से बड़ी खबर।"
                else:
                    announcement = f"{gs_paper} — {cat_hindi} की खबर।"
            elif breaking:
                announcement = f"ब्रेकिंग न्यूज़! {cat_hindi} की बड़ी खबर।"
            else:
                announcement = f"अब {cat_hindi} की खबर।"

            ann_path = self.text_to_speech(
                announcement, f"announcement_{i:02d}", slow=False
            )
            if ann_path:
                audio_files[f"announcement_{i}"] = str(ann_path)

            # Headline
            headline = segment.get("headline_hindi", "")
            if headline:
                path = self.text_to_speech(headline, f"headline_{i:02d}", slow=False)
                if path:
                    audio_files[f"headline_{i}"] = str(path)

            # Main narration
            seg_path = self.generate_segment_audio(segment, i)
            if seg_path:
                audio_files[f"segment_{i}"] = str(seg_path)

        # Show outro
        logger.info("Generating show outro audio...")
        outro_text = show_data.get("outro_hindi", "")
        if not outro_text:
            if upsc_mode:
                outro_text = "यह थे आज के UPSC करंट अफेयर्स। पढ़ते रहो, आगे बढ़ते रहो।"
            else:
                outro_text = "यह थीं आज की प्रमुख खबरें। जुड़े रहिए हमारे साथ।"
        full_outro = f"{outro_text} हमारे चैनल को सब्सक्राइब करें। धन्यवाद!"
        path = self.text_to_speech(full_outro, "outro", slow=False)
        if path:
            audio_files["outro"] = str(path)

        logger.info(f"Generated {len(audio_files)} audio files")
        return audio_files

    def get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds."""
        try:
            from moviepy import AudioFileClip
            with AudioFileClip(audio_path) as clip:
                return clip.duration
        except Exception as e:
            logger.warning(f"Could not get duration of {audio_path}: {e}")
            # Estimate: ~3 chars/second for Hindi TTS
            return 5.0

    def _clean_for_tts(self, text: str) -> str:
        """Clean text for better TTS output."""
        if not text:
            return ""

        # Remove pause markers (used for visual timing, not TTS)
        text = text.replace("[रुकिए...]", ", ")
        text = text.replace("[PAUSE]", ", ")

        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)

        # Remove excessive punctuation
        text = re.sub(r"[!]{2,}", "!", text)
        text = re.sub(r"[.]{3,}", "...", text)

        # Clean whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _enhance_narration(self, narration: str, segment: dict) -> str:
        """Add context and flow to narration text."""
        emotion = segment.get("emotion", "")
        breaking = segment.get("breaking", False)

        # Add emphasis prefix for breaking news
        if breaking and not narration.startswith("ब्रेकिंग"):
            narration = narration

        return narration


def _get_hindi_date_text() -> str:
    """Return Hindi date string for audio."""
    from datetime import datetime

    now = datetime.now()
    months = [
        "जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून",
        "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर",
    ]
    days = [
        "सोमवार", "मंगलवार", "बुधवार", "गुरुवार",
        "शुक्रवार", "शनिवार", "रविवार",
    ]
    return f"आज है {days[now.weekday()]}, {now.day} {months[now.month - 1]} {now.year}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tts = TTSGenerator(output_dir="/tmp/test_audio")

    test_texts = [
        "नमस्कार! आज की बड़ी खबरें लेकर हम आ गए हैं।",
        "ब्रेकिंग न्यूज़! भारत ने एक नया इतिहास रच दिया है।",
        "यह थीं आज की मुख्य खबरें। धन्यवाद!",
    ]

    for i, text in enumerate(test_texts, 1):
        path = tts.text_to_speech(text, f"test_{i}")
        if path:
            duration = tts.get_audio_duration(str(path))
            print(f"Generated: {path} ({duration:.1f}s)")
