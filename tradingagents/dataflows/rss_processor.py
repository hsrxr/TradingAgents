from langchain_core.tools import tool
from typing import Annotated
import json
import sqlite3
import hashlib
import urllib.request
import xml.etree.ElementTree as ET
from urllib.error import URLError
from email.utils import parsedate_to_datetime
import re
import html
from datetime import timezone

# Configuration constants
DB_FILE = "crypto_news.db"
MAPPING_FILE = "id_mapping.json"
RSS_FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed"
}

def _init_db():
    """Internal helper to initialize the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            url_hash TEXT PRIMARY KEY,
            url TEXT,
            title TEXT,
            summary TEXT,
            pub_time TEXT,
            source TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def _fetch_rss_xml(url: str) -> bytes | None:
    """Internal helper to fetch the raw XML from the RSS feed."""
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read()
    except URLError as e:
        print(f"Failed to fetch {url}: {e}")
        return None

def _clean_html(raw_html: str) -> str:
    """Internal helper to remove HTML tags and unescape HTML entities."""
    if not raw_html:
        return "No Summary"
    # Strip HTML tags using regex
    clean_text = re.sub(r'<.*?>', '', raw_html)
    # Unescape HTML entities (e.g., &amp; to &) and strip whitespace
    return html.unescape(clean_text).strip()

def _parse_pub_time_to_timestamp(pub_time: str) -> int:
    """Parse RSS pubDate to UNIX timestamp for robust sorting."""
    if not pub_time:
        return 0

    try:
        dt = parsedate_to_datetime(pub_time)
        if dt is None:
            return 0
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except (TypeError, ValueError, OverflowError):
        return 0

@tool
def fetch_and_parse_crypto_news(
    limit: Annotated[int, "Maximum number of most-recent pending articles to return to the agent, default is 50"] = 50
) -> str:
    """
    Fetches the latest cryptocurrency news from CoinDesk, Cointelegraph, and Decrypt RSS feeds.
    Parses the XML, cleans HTML from summaries, stores new articles in a local SQLite database,
    and returns the latest articles from the entire database sorted by publication time (newest first),
    containing incremental IDs, titles, and summaries for the agent to evaluate.
    
    :param limit: Maximum number of newest pending articles to retrieve in this batch.
    :return: A JSON string containing a list of dictionaries with article metadata.
    """
    _init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Fetch and store new articles
    for source_name, feed_url in RSS_FEEDS.items():
        xml_data = _fetch_rss_xml(feed_url)
        if not xml_data:
            continue
            
        try:
            root = ET.fromstring(xml_data)
            for item in root.findall('./channel/item'):
                title = item.findtext('title') or 'No Title'
                url = item.findtext('link') or ''
                pub_time = item.findtext('pubDate') or 'Unknown Date'
                
                # Clean the summary right after extraction
                raw_summary = item.findtext('description') or ''
                summary = _clean_html(raw_summary)
                
                if not url:
                    continue
                    
                url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO articles 
                    (url_hash, url, title, summary, pub_time, source, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (url_hash, url, title, summary, pub_time, source_name, 'PENDING'))
                
        except ET.ParseError as e:
            print(f"XML parsing error for {source_name}: {e}")

    conn.commit()

    # 2. Extract latest articles from the entire database, then apply limit
    cursor.execute('''
        SELECT url_hash, title, summary, pub_time, source, status
        FROM articles 
    ''')

    recent_articles = cursor.fetchall()
    recent_articles.sort(key=lambda article: _parse_pub_time_to_timestamp(article[3]), reverse=True)
    recent_articles = recent_articles[:limit]
    
    agent_payload = []
    id_mapping = {}
    
    # 3. Generate incremental IDs for this specific batch
    for incremental_id, article in enumerate(recent_articles, start=1):
        url_hash, title, summary, pub_time, source, status = article
        
        id_mapping[str(incremental_id)] = url_hash
        
        agent_payload.append({
            "id": incremental_id,
            "source": source,
            "title": title,
            "pub_time": pub_time,
            "summary": summary,
            "status": status,
        })

    conn.close()

    # 4. Save the ID mapping locally for the subsequent retrieval tool
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(id_mapping, f, ensure_ascii=False, indent=4)

    # 5. Return the JSON string for the agent
    return json.dumps(agent_payload, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # For testing purposes, you can run this script directly to see the output
    # print(fetch_and_parse_crypto_news())
    pass