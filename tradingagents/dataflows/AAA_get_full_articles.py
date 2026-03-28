import os
import json
import sqlite3
import urllib.request
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
from typing import Annotated, List
from langchain_core.tools import tool

# 配置文件与常量
DB_FILE = "crypto_news.db"
MAPPING_FILE = "id_mapping.json"
ARTICLE_DIR = "tradingagents\\dataflows\\data_cache\\articles"

# 确保文章保存目录存在
os.makedirs(ARTICLE_DIR, exist_ok=True)

def _ensure_filepath_column():
    """辅助函数：检查数据库是否包含 file_path 列，如果没有则自动添加"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(articles)")
    columns = [col[1] for col in cursor.fetchall()]
    if "file_path" not in columns:
        cursor.execute("ALTER TABLE articles ADD COLUMN file_path TEXT")
        conn.commit()
    conn.close()

def _scrape_and_clean_html(url: str, source: str) -> str | None:
    """
    核心爬虫路由与清洗机制。根据不同的新闻源采用不同的提取策略。
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read().decode('utf-8')
    except HTTPError as e:
        print(f"HTTP Error {e.code} fetching URL {url} (可能被反爬拦截)")
        return None
    except URLError as e:
        print(f"URL Error fetching URL {url}: {e}")
        return None
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    paragraphs = []

    # 路由机制：根据来源使用不同的 CSS 选择器
    if source == "CoinDesk":
        # CoinDesk 的正文通常在特定的 div 或者是带有特定 class 的 p 标签中
        container = soup.find('main') or soup.find('article')
        if container:
            paragraphs = container.find_all('p')
            
    elif source == "Cointelegraph":
        # Cointelegraph 的正文通常在 class 包含 'post-content' 的 div 里
        container = soup.find('div', class_=lambda c: c and 'post-content' in c)
        if container:
            paragraphs = container.find_all('p')
            
    elif source == "Decrypt":
        container = soup.find('div', class_=lambda c: c and 'prose' in c)
        if not container:
            container = soup.find('article') or soup.find('main')
        
        if container:
            # Decrypt 有时会在段落外再包一层 div，所以这里放宽查找范围
            paragraphs = container.find_all('p')

    # Fallback (兜底机制)：如果路由规则失效（网站改版），则提取全局的段落
    if not paragraphs:
        paragraphs = soup.find_all('p')

    # 清洗文本：过滤掉过短的无用段落（如导航链接、版权声明等）
    clean_text = []
    for p in paragraphs:
        text = p.get_text(strip=True)

        if len(text) > 30 and "By clicking" not in text and "Sign up" not in text:
            clean_text.append(text)

    if not clean_text:
        return None

    return "\n\n".join(clean_text)

@tool
def fetch_article_full_text(
    article_ids: Annotated[List[int], "A list of article IDs (integers) that the agent wants to read in full."]
) -> str:
    """
    Retrieves the full text of selected articles based on their IDs.
    It looks up the URL, scrapes the content using source-specific parsers, 
    saves the raw text locally, updates the database status, and returns the clean text to the agent.
    
    :param article_ids: List of article IDs chosen from the pending news list.
    :return: A JSON string containing the full text of the requested articles.
    """
    _ensure_filepath_column()
    
    # 1. 加载 ID 到 hash 的映射表
    if not os.path.exists(MAPPING_FILE):
        return json.dumps({"error": "Mapping file not found. Please fetch news list first."})
        
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        id_mapping = json.load(f)

    # 2. 将 Agent 传入的 IDs 转换为 url_hashes
    target_hashes = []
    for aid in article_ids:
        aid_str = str(aid)
        if aid_str in id_mapping:
            target_hashes.append(id_mapping[aid_str])

    if not target_hashes:
        return json.dumps({"error": "No valid article IDs found."})

    # 3. 从数据库中获取文章信息（包含状态）
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(target_hashes))
    cursor.execute(f'''
        SELECT url_hash, url, title, source, status, file_path
        FROM articles 
        WHERE url_hash IN ({placeholders})
    ''', target_hashes)
    
    articles_to_fetch = cursor.fetchall()
    results_for_agent = []

    # 4. 遍历执行爬取、保存和状态更新
    for url_hash, url, title, source, status, file_path in articles_to_fetch:
        # 已抓取成功：直接返回缓存文件内容
        if status == 'FETCHED':
            cached_content = ""
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as text_file:
                        file_content = text_file.read()
                        content_lines = file_content.splitlines()
                        cached_content = "\n".join(content_lines[3:]) if len(content_lines) > 3 else ""
                except Exception as e:
                    print(f"Error reading cached file {file_path}: {e}")

            results_for_agent.append({
                "title": title,
                "source": source,
                "content": cached_content
            })
            continue

        # 历史错误记录：按要求返回空内容
        if status == 'ERROR':
            results_for_agent.append({
                "title": title,
                "source": source,
                "content": "ERROR: Failed to fetch or parse the full article content."
            })
            continue

        # 仅对 PENDING 状态执行抓取
        if status != 'PENDING':
            continue

        print(f"Fetching full text for [{source}]: {title}...")
        print(f"URL: {url}")
        
        full_text = _scrape_and_clean_html(url, source)
        
        if full_text:
            # 成功爬取：保存到本地
            file_path = os.path.join(ARTICLE_DIR, f"{url_hash}.txt")
            try:
                with open(file_path, 'w', encoding='utf-8') as text_file:
                    text_file.write(f"Title: {title}\nSource: {source}\nURL: {url}\n\n")
                    text_file.write(full_text)
                
                # 更新数据库状态
                cursor.execute('''
                    UPDATE articles 
                    SET status = 'FETCHED', file_path = ? 
                    WHERE url_hash = ?
                ''', (file_path, url_hash))
                
                # 组装返回给 Agent 的数据
                results_for_agent.append({
                    "title": title,
                    "source": source,
                    "content": full_text
                })
            except Exception as e:
                print(f"Error saving file {file_path}: {e}")
                cursor.execute("UPDATE articles SET status = 'ERROR' WHERE url_hash = ?", (url_hash,))
        else:
            # 爬取失败
            cursor.execute("UPDATE articles SET status = 'ERROR' WHERE url_hash = ?", (url_hash,))
            results_for_agent.append({
                "title": title,
                "source": source,
                "content": "ERROR: Failed to fetch or parse the full article content."
            })

    conn.commit()
    conn.close()

    # 5. 返回干净的 JSON 数据给 Agent
    return json.dumps(results_for_agent, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # 供本地测试使用
    test_ids = [2, 7]  # 替换为实际存在的 ID
    print(fetch_article_full_text(test_ids))