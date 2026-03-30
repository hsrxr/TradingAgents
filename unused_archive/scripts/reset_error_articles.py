#!/usr/bin/env python3
"""
脚本用途：将数据库中所有 status='ERROR' 的记录重置为 'PENDING'，以便重新尝试爬取。
"""

import sqlite3

DB_FILE = "crypto_news.db"

def reset_error_articles():
    """将所有错误状态的文章重置为 PENDING 状态"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 首先查询有多少条 ERROR 记录
        cursor.execute("SELECT COUNT(*) FROM articles WHERE status = 'ERROR'")
        error_count = cursor.fetchone()[0]
        
        if error_count == 0:
            print("数据库中没有 ERROR 状态的记录。")
            return
        
        print(f"发现 {error_count} 条 ERROR 状态的记录，准备重置为 PENDING...")
        
        # 更新所有 ERROR 状态为 PENDING
        cursor.execute("UPDATE articles SET status = 'PENDING' WHERE status = 'ERROR'")
        affected_rows = cursor.rowcount
        
        # 提交事务
        conn.commit()
        conn.close()
        
        print(f"✓ 成功更新 {affected_rows} 条记录为 PENDING 状态")
        
    except sqlite3.Error as e:
        print(f"✗ 数据库错误: {e}")
    except Exception as e:
        print(f"✗ 未知错误: {e}")

if __name__ == "__main__":
    reset_error_articles()
