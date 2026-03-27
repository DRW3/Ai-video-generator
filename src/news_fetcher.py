"""
News Fetcher - Retrieves latest news from multiple RSS feeds and News APIs
Supports: Google News RSS, BBC, Reuters, Al Jazeera, Times of India, NDTV,
          PIB, The Hindu Editorial, PRS India — with UPSC mode.
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import json
import re
import html
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Top global + Indian news RSS feeds
RSS_FEEDS = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.reuters.com/reuters/worldNews",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "India": [
        "https://feeds.feedburner.com/ndtvnews-top-stories",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://www.thehindu.com/news/national/feeder/default.rss",
    ],
    "Technology": [
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.wired.com/feed/rss",
    ],
    "Science": [
        "https://www.sciencedaily.com/rss/top.xml",
    ],
    "Sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
}

# Google News RSS (no API key needed)
GOOGLE_NEWS_RSS = {
    "Top Stories": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "World": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "Technology": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "Business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TlhRU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "Science": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNR1ptZHpJU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "Entertainment": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
}

# ─── UPSC-specific feeds ────────────────────────────────────────────────────
# These cover PIB, editorial opinions, Parliament, economy, and environment —
# the five pillars of GS preparation.
UPSC_RSS_FEEDS = {
    "Polity & Governance": [
        # PIB — official government press releases (schemes, policies, laws)
        "https://pib.gov.in/RssMain.aspx",
        # PRS India — Parliament bills, committee reports
        "https://www.prsindia.org/feed",
    ],
    "Economy & Finance": [
        "https://www.thehindu.com/business/Economy/feeder/default.rss",
        "https://feeds.bbci.co.uk/news/business/economy/rss.xml",
    ],
    "Environment & Ecology": [
        "https://www.downtoearth.org.in/rss/news",
        "https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss",
    ],
    "International Relations": [
        "https://www.thehindu.com/news/international/feeder/default.rss",
        "https://rss.reuters.com/reuters/worldNews",
    ],
    "Science & Technology": [
        "https://www.thehindu.com/sci-tech/technology/feeder/default.rss",
        "https://www.sciencedaily.com/rss/top.xml",
    ],
    "History & Culture": [
        "https://www.thehindu.com/arts/history-and-culture/feeder/default.rss",
    ],
    "Social Issues": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
    ],
    "Editorial": [
        # The Hindu editorial — best for UPSC opinion/analysis
        "https://www.thehindu.com/opinion/editorial/feeder/default.rss",
        "https://indianexpress.com/section/opinion/editorials/feed/",
    ],
}

# Google News searches tuned for UPSC current-affairs topics
UPSC_GOOGLE_NEWS = {
    "Polity & Governance": "https://news.google.com/rss/search?q=India+parliament+bill+supreme+court+constitution+scheme&hl=en-IN&gl=IN&ceid=IN:en",
    "Economy & Finance":   "https://news.google.com/rss/search?q=India+economy+RBI+budget+GDP+inflation+finance&hl=en-IN&gl=IN&ceid=IN:en",
    "Environment & Ecology": "https://news.google.com/rss/search?q=India+environment+climate+biodiversity+pollution+forest&hl=en-IN&gl=IN&ceid=IN:en",
    "International Relations": "https://news.google.com/rss/search?q=India+foreign+policy+bilateral+UN+ASEAN+SCO+G20&hl=en-IN&gl=IN&ceid=IN:en",
    "Science & Technology": "https://news.google.com/rss/search?q=India+ISRO+DRDO+science+technology+innovation+space&hl=en-IN&gl=IN&ceid=IN:en",
    "Social Issues":        "https://news.google.com/rss/search?q=India+education+health+poverty+women+tribal+welfare&hl=en-IN&gl=IN&ceid=IN:en",
}


def _clean_html(raw_html: str) -> str:
    """Remove HTML tags and decode entities."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", "", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fetch_url(url: str, timeout: int = 15) -> Optional[bytes]:
    """Fetch URL with user-agent spoofing."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def _parse_rss(content: bytes, category: str) -> list[dict]:
    """Parse RSS XML and extract articles."""
    articles = []
    try:
        root = ET.fromstring(content)
        # Handle both RSS and Atom namespaces
        ns = {"media": "http://search.yahoo.com/mrss/"}

        channel = root.find("channel")
        if channel is None:
            channel = root  # Atom feed fallback

        items = channel.findall("item") or root.findall(
            ".//{http://www.w3.org/2005/Atom}entry"
        )

        for item in items[:8]:  # Top 8 per feed
            title_el = item.find("title")
            desc_el = item.find("description") or item.find(
                "{http://www.w3.org/2005/Atom}summary"
            )
            link_el = item.find("link")
            pub_el = item.find("pubDate") or item.find(
                "{http://www.w3.org/2005/Atom}published"
            )

            title = _clean_html(title_el.text or "") if title_el is not None else ""
            description = _clean_html(desc_el.text or "") if desc_el is not None else ""
            link = (link_el.text or "").strip() if link_el is not None else ""
            pub_date = (pub_el.text or "").strip() if pub_el is not None else ""

            # Skip sponsored / empty titles
            if not title or len(title) < 10:
                continue
            if any(
                skip in title.lower()
                for skip in ["advertisement", "sponsored", "subscribe now"]
            ):
                continue

            articles.append(
                {
                    "title": title,
                    "description": description[:500],
                    "link": link,
                    "published": pub_date,
                    "category": category,
                    "source": "",
                }
            )
    except ET.ParseError as e:
        logger.warning(f"XML parse error: {e}")
    return articles


def fetch_google_news(categories: list[str] | None = None) -> list[dict]:
    """Fetch from Google News RSS feeds."""
    all_articles = []
    feeds = (
        {k: v for k, v in GOOGLE_NEWS_RSS.items() if k in categories}
        if categories
        else GOOGLE_NEWS_RSS
    )

    for category, url in feeds.items():
        logger.info(f"Fetching Google News: {category}")
        content = _fetch_url(url)
        if content:
            articles = _parse_rss(content, category)
            for a in articles:
                a["source"] = f"Google News - {category}"
            all_articles.extend(articles)
            logger.info(f"  Got {len(articles)} articles")

    return all_articles


def fetch_rss_feeds(categories: list[str] | None = None) -> list[dict]:
    """Fetch from curated RSS feeds."""
    all_articles = []
    feeds = (
        {k: v for k, v in RSS_FEEDS.items() if k in categories}
        if categories
        else RSS_FEEDS
    )

    for category, urls in feeds.items():
        for url in urls:
            logger.info(f"Fetching {category}: {url}")
            content = _fetch_url(url, timeout=10)
            if content:
                articles = _parse_rss(content, category)
                for a in articles:
                    a["source"] = url.split("/")[2]  # domain as source
                all_articles.extend(articles)
                logger.info(f"  Got {len(articles)} articles from {url}")

    return all_articles


def deduplicate(articles: list[dict], max_per_category: int = 5) -> list[dict]:
    """Remove duplicate headlines and limit per category."""
    seen_titles = set()
    by_category: dict[str, list] = {}

    for article in articles:
        # Normalize title for dedup
        normalized = re.sub(r"\W+", " ", article["title"].lower()).strip()
        key = " ".join(normalized.split()[:6])  # first 6 words as key

        if key in seen_titles:
            continue
        seen_titles.add(key)

        cat = article["category"]
        if cat not in by_category:
            by_category[cat] = []
        if len(by_category[cat]) < max_per_category:
            by_category[cat].append(article)

    # Flatten preserving category diversity
    result = []
    max_total = sum(len(v) for v in by_category.values())
    round_robin = list(by_category.values())
    while any(round_robin) and len(result) < max_total:
        for cat_list in round_robin:
            if cat_list:
                result.append(cat_list.pop(0))

    return result


def fetch_upsc_news(categories: list[str] | None = None) -> list[dict]:
    """Fetch UPSC-specific news from PIB, PRS, editorial, and topic-search feeds."""
    all_articles = []

    # Topic-search Google News feeds
    gnews = (
        {k: v for k, v in UPSC_GOOGLE_NEWS.items() if k in categories}
        if categories
        else UPSC_GOOGLE_NEWS
    )
    for category, url in gnews.items():
        logger.info(f"Fetching UPSC Google News: {category}")
        content = _fetch_url(url)
        if content:
            articles = _parse_rss(content, category)
            for a in articles:
                a["source"] = f"Google News – {category}"
                a["upsc_relevant"] = True
            all_articles.extend(articles)

    # Curated UPSC RSS feeds
    rss = (
        {k: v for k, v in UPSC_RSS_FEEDS.items() if k in categories}
        if categories
        else UPSC_RSS_FEEDS
    )
    for category, urls in rss.items():
        for url in urls:
            logger.info(f"Fetching UPSC RSS [{category}]: {url}")
            content = _fetch_url(url, timeout=10)
            if content:
                articles = _parse_rss(content, category)
                for a in articles:
                    a["source"] = url.split("/")[2]
                    a["upsc_relevant"] = True
                all_articles.extend(articles)

    logger.info(f"UPSC feeds total: {len(all_articles)} articles")
    return all_articles


def get_latest_news(
    max_articles: int = 20,
    use_google_news: bool = True,
    use_rss_feeds: bool = True,
    upsc_mode: bool = False,
    categories: list[str] | None = None,
) -> list[dict]:
    """
    Main entry point: fetch, deduplicate, and return latest news articles.

    Args:
        upsc_mode: When True, prioritises UPSC-relevant feeds (PIB, PRS,
                   editorial, topic-search Google News for GS topics).

    Returns list of dicts with keys:
        title, description, link, published, category, source, upsc_relevant
    """
    all_articles = []

    if upsc_mode:
        # UPSC feeds come first so they dominate after dedup
        upsc_cats = categories  # pass caller's filter through
        articles = fetch_upsc_news(upsc_cats)
        all_articles.extend(articles)
        logger.info(f"UPSC feeds total: {len(articles)}")

    if use_google_news:
        articles = fetch_google_news(categories)
        all_articles.extend(articles)
        logger.info(f"Google News total: {len(articles)}")

    if use_rss_feeds:
        articles = fetch_rss_feeds(categories)
        all_articles.extend(articles)
        logger.info(f"RSS Feeds total: {len(articles)}")

    # Deduplicate and diversify
    max_per_cat = 4 if upsc_mode else 6
    deduped = deduplicate(all_articles, max_per_category=max_per_cat)
    result = deduped[:max_articles]

    logger.info(f"Final articles after dedup: {len(result)}")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = get_latest_news(max_articles=15, use_rss_feeds=False)
    print(f"\n=== {len(articles)} Articles Fetched ===\n")
    for i, a in enumerate(articles, 1):
        print(f"{i}. [{a['category']}] {a['title']}")
        print(f"   Source: {a['source']}")
        if a["description"]:
            print(f"   {a['description'][:100]}...")
        print()
