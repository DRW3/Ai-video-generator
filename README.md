# 🎬 AI News Video Generator — हिंदी न्यूज़ वीडियो

**Generate stunning Hindi news broadcast videos automatically using Claude AI + gTTS + MoviePy**

> Fetches real-time news → AI processes it into dramatic scripts → Hindi TTS narration → Animated video!

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🌍 **Live News** | Fetches from Google News RSS, BBC, Reuters, NDTV, TOI |
| 🤖 **Claude AI** | Transforms boring articles into dramatic Hindi scripts |
| 🔊 **Hindi TTS** | Natural Hindi audio narration via Google TTS |
| 🎬 **Animated Video** | Cinematic dark theme with animated cards, tickers, effects |
| ⚡ **Breaking News** | Auto-detects high-impact stories with special treatment |
| 📺 **News Ticker** | Scrolling lower-third news ticker |
| 🎨 **Category Colors** | Color-coded segments per category |
| 📊 **Impact Score** | Claude rates story importance 1-10 |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# System requirement
sudo apt-get install ffmpeg    # Ubuntu/Debian
# brew install ffmpeg          # macOS

# Python packages
pip install -r requirements.txt
```

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY="your-claude-api-key-here"
```

### 3. Run!

```bash
python src/main.py
```

---

## 📋 Usage

```bash
# Basic run (fetch 8 news articles, full video)
python src/main.py

# Custom number of articles
python src/main.py --max-news 12

# Specific categories only
python src/main.py --categories "India,Technology,Sports"

# Skip video (faster - just script + audio)
python src/main.py --no-video

# Generate preview thumbnail only
python src/main.py --preview

# Use existing script (skip fetch + AI)
python src/main.py --script-file output/scripts/show_data_20240317_120000.json

# Custom output directory
python src/main.py --output /path/to/output

# Debug mode
python src/main.py --debug
```

---

## 📁 Project Structure

```
Ai-video-generator/
├── src/
│   ├── main.py              # Orchestrator — run this!
│   ├── news_fetcher.py      # Fetches news from RSS feeds
│   ├── content_processor.py # Claude AI script generation
│   ├── tts_generator.py     # Hindi TTS audio generation
│   └── video_renderer.py    # Animated video creation
├── output/
│   ├── videos/              # Final MP4 videos
│   ├── audio/               # Hindi TTS MP3 files
│   ├── scripts/             # JSON scripts (reusable)
│   └── previews/            # Thumbnail images
├── config.json              # Configuration
├── requirements.txt         # Python dependencies
└── .env.example             # API key template
```

---

## 🎨 Video Style

The generated video features:
- **Dark cinematic background** with animated grid and gradient
- **Color-coded category banners** (red for World, blue for Tech, etc.)
- **Animated news cards** with slide-in effects
- **Typewriter headline reveals** with glow effects
- **Breaking news banners** with pulsing red animation
- **Scrolling Hindi ticker** at the bottom
- **Impact meter** showing story importance
- **Smooth transitions** between segments
- **Dramatic intro/outro** with rotating particle effects

---

## 📰 News Sources

| Source | Category |
|--------|----------|
| Google News (India) | Top Stories, World, Tech, Business |
| BBC News | World, Sports, Business |
| Reuters | World News |
| Al Jazeera | World |
| NDTV | India |
| Times of India | India |
| The Hindu | India |
| TechCrunch | Technology |
| Wired | Technology |
| ScienceDaily | Science |

---

## ⚙️ Configuration (`config.json`)

```json
{
  "max_news": 8,              // Number of articles
  "categories": null,         // null = all, or ["India", "Technology"]
  "use_google_news": true,    // Use Google News RSS
  "use_rss_feeds": true,      // Use other RSS feeds
  "generate_audio": true,     // Generate Hindi TTS
  "generate_video": true,     // Render video
  "output_dir": "output"      // Output directory
}
```

---

## 🔧 Requirements

- Python 3.10+
- ffmpeg (system package)
- Anthropic API key (Claude)
- Internet connection (news fetching + gTTS)

---

## 📺 Output Example

```
╔══════════════════════════════════════════════════════════════╗
║         🎬 AI NEWS VIDEO GENERATOR — हिंदी न्यूज़ वीडियो         ║
╚══════════════════════════════════════════════════════════════╝

📰 Fetched Headlines:
   1. [Top Stories ] AI breakthrough changes scientific research
   2. [India       ] India launches new economic initiative
   3. [Technology  ] New chip architecture promises 10x performance
   ...

🎬 Generated Show Segments:
  Title: आज की बड़ी खबरें
   1. [Technology  ] AI ने बदल दिया विज्ञान का इतिहास! ⚡BREAKING
   2. [India       ] भारत की नई आर्थिक क्रांति!
   3. [Technology  ] नया चिप — 10 गुना तेज़ प्रोसेसर!

🔊 Audio: 18 files, ~145s total
🖼️  Preview: output/previews/thumbnail_20240317_120000.png
🎥 Video: output/videos/news_technology_20240317_120000.mp4

   ▶  ffplay 'output/videos/news_technology_20240317_120000.mp4'
```

---

## 📝 License

MIT License — Free to use, modify, and distribute.
