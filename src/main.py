"""
AI News Video Generator - Main Orchestrator
===========================================
Fetches latest news → Claude AI processes → Hindi TTS → Animated Video

Usage:
    python src/main.py
    python src/main.py --categories "World,India,Technology" --max-news 10
    python src/main.py --no-fetch --script-file output/scripts/show_data.json
    python src/main.py --no-video  # Only generate script + audio
    python src/main.py --preview   # Only render preview image
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from news_fetcher import get_latest_news
from content_processor import ContentProcessor
from tts_generator import TTSGenerator
from video_renderer import VideoRenderer

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("output/generator.log", mode="a"),
    ],
)
logger = logging.getLogger("main")

# Default config
DEFAULT_CONFIG = {
    "max_news": 8,
    "categories": None,  # None = all categories
    "use_google_news": True,
    "use_rss_feeds": True,
    "output_dir": "output",
    "video_filename": None,  # Auto-generated if None
    "generate_video": True,
    "generate_audio": True,
    "save_scripts": True,
}


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from file."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                user_config = json.load(f)
            config.update(user_config)
            logger.info(f"Loaded config from {config_path}")
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
    return config


def ensure_output_dirs(output_dir: str):
    """Create output directory structure."""
    dirs = [
        output_dir,
        f"{output_dir}/audio",
        f"{output_dir}/scripts",
        f"{output_dir}/videos",
        f"{output_dir}/previews",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def generate_video_filename(show_data: dict) -> str:
    """Generate timestamped filename for the video."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    segments = show_data.get("segments", [])
    top_cat = segments[0].get("category", "news") if segments else "news"
    return f"news_{top_cat.lower()}_{ts}.mp4"


def print_banner():
    """Print startup banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║         🎬 AI NEWS VIDEO GENERATOR — हिंदी न्यूज़ वीडियो         ║
║         Powered by Claude AI + gTTS + MoviePy               ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_pipeline(args, config: dict) -> dict:
    """
    Run the full video generation pipeline.

    Returns:
        dict with output paths and stats
    """
    start_time = time.time()
    output_dir = config["output_dir"]
    ensure_output_dirs(output_dir)

    results = {
        "articles_fetched": 0,
        "segments_generated": 0,
        "audio_files": {},
        "video_path": None,
        "preview_path": None,
        "script_path": None,
        "duration_seconds": 0,
    }

    # ─────────────────────────────────────────────
    # STEP 1: FETCH NEWS
    # ─────────────────────────────────────────────
    if hasattr(args, "script_file") and args.script_file:
        logger.info(f"Loading show data from {args.script_file}")
        with open(args.script_file) as f:
            show_data = json.load(f)
        logger.info(
            f"Loaded show with {len(show_data.get('segments', []))} segments"
        )
    else:
        logger.info("=" * 60)
        logger.info("STEP 1: Fetching latest news...")
        logger.info("=" * 60)

        categories = config.get("categories")
        if isinstance(categories, str):
            categories = [c.strip() for c in categories.split(",")]

        articles = get_latest_news(
            max_articles=config["max_news"],
            use_google_news=config["use_google_news"],
            use_rss_feeds=config["use_rss_feeds"],
            categories=categories,
        )

        results["articles_fetched"] = len(articles)
        logger.info(f"Fetched {len(articles)} articles")

        if not articles:
            logger.error("No articles fetched! Check network connection.")
            return results

        # Print fetched headlines
        print("\n📰 Fetched Headlines:")
        for i, a in enumerate(articles, 1):
            print(f"  {i:2d}. [{a['category']:12s}] {a['title'][:70]}")

        # ─────────────────────────────────────────────
        # STEP 2: PROCESS WITH CLAUDE AI
        # ─────────────────────────────────────────────
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Processing with Claude AI...")
        logger.info("=" * 60)

        processor = ContentProcessor()
        show_data = processor.process_news(articles)
        results["segments_generated"] = len(show_data.get("segments", []))

        # Save script
        if config["save_scripts"]:
            script_path = f"{output_dir}/scripts/show_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(show_data, f, ensure_ascii=False, indent=2)
            results["script_path"] = script_path
            logger.info(f"Script saved: {script_path}")

        # Print generated segments
        print("\n🎬 Generated Show Segments:")
        print(f"  Title: {show_data.get('show_title', '')}")
        for seg in show_data.get("segments", []):
            breaking_tag = " ⚡BREAKING" if seg.get("breaking") else ""
            print(
                f"  {seg['id']:2d}. [{seg['category']:12s}] {seg.get('headline_hindi', '')[:50]}{breaking_tag}"
            )

    # ─────────────────────────────────────────────
    # STEP 3: GENERATE HINDI TTS AUDIO
    # ─────────────────────────────────────────────
    audio_files = {}

    if config.get("generate_audio", True):
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: Generating Hindi TTS Audio...")
        logger.info("=" * 60)

        tts = TTSGenerator(output_dir=f"{output_dir}/audio")
        audio_files = tts.generate_show_audio(show_data)
        results["audio_files"] = audio_files

        total_duration = 0.0
        for key, path in audio_files.items():
            dur = tts.get_audio_duration(path)
            total_duration += dur
            logger.debug(f"  Audio: {key} → {dur:.1f}s")

        logger.info(
            f"Generated {len(audio_files)} audio files (~{total_duration:.0f}s total)"
        )
        print(f"\n🔊 Audio: {len(audio_files)} files, ~{total_duration:.0f}s total")

    # ─────────────────────────────────────────────
    # STEP 4: RENDER VIDEO
    # ─────────────────────────────────────────────
    renderer = VideoRenderer(output_dir=f"{output_dir}/videos")

    # Always generate preview image
    preview_path = f"{output_dir}/previews/thumbnail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    try:
        renderer.render_preview_image(show_data, preview_path)
        results["preview_path"] = preview_path
        print(f"\n🖼️  Preview: {preview_path}")
    except Exception as e:
        logger.warning(f"Preview generation failed: {e}")

    if config.get("generate_video", True):
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: Rendering Video...")
        logger.info("=" * 60)

        video_filename = config.get("video_filename") or generate_video_filename(show_data)
        try:
            video_path = renderer.render_full_show(
                show_data=show_data,
                audio_files=audio_files,
                output_filename=video_filename,
            )
            results["video_path"] = video_path
        except Exception as e:
            logger.error(f"Video rendering failed: {e}", exc_info=True)
            print(f"\n❌ Video rendering failed: {e}")
            print("   Script and audio files are still available.")

    # ─────────────────────────────────────────────
    # FINAL SUMMARY
    # ─────────────────────────────────────────────
    elapsed = time.time() - start_time
    results["duration_seconds"] = elapsed

    print("\n" + "=" * 60)
    print("✅ GENERATION COMPLETE!")
    print("=" * 60)
    print(f"⏱️  Total time: {elapsed:.1f}s")
    print(f"📰 Articles fetched: {results['articles_fetched']}")
    print(f"🎬 Segments generated: {results['segments_generated']}")
    print(f"🔊 Audio files: {len(results['audio_files'])}")
    if results.get("script_path"):
        print(f"📝 Script: {results['script_path']}")
    if results.get("preview_path"):
        print(f"🖼️  Preview: {results['preview_path']}")
    if results.get("video_path"):
        print(f"🎥 Video: {results['video_path']}")
        print(f"\n   ▶  ffplay '{results['video_path']}'")
        print(f"   ▶  vlc '{results['video_path']}'")
    print("=" * 60)

    return results


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="AI News Video Generator — Hindi News Show"
    )
    parser.add_argument(
        "--max-news",
        type=int,
        default=8,
        help="Maximum number of news articles to fetch (default: 8)",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Comma-separated categories (e.g., 'World,India,Technology')",
    )
    parser.add_argument(
        "--no-google",
        action="store_true",
        help="Disable Google News RSS",
    )
    parser.add_argument(
        "--no-rss",
        action="store_true",
        help="Disable other RSS feeds",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Skip audio generation",
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Skip video rendering (only script + audio)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Only generate preview thumbnail",
    )
    parser.add_argument(
        "--script-file",
        type=str,
        default=None,
        help="Load existing show script JSON instead of fetching news",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Config file path (default: config.json)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load + merge config
    config = load_config(args.config)
    config.update(
        {
            "max_news": args.max_news,
            "categories": args.categories,
            "use_google_news": not args.no_google,
            "use_rss_feeds": not args.no_rss,
            "generate_audio": not args.no_audio,
            "generate_video": not args.no_video and not args.preview,
            "output_dir": args.output,
        }
    )

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n❌ ERROR: ANTHROPIC_API_KEY environment variable not set!")
        print("   Export your API key:")
        print("   export ANTHROPIC_API_KEY='your-api-key-here'")
        sys.exit(1)

    run_pipeline(args, config)


if __name__ == "__main__":
    main()
