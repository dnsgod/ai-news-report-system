import sqlite3
from pathlib import Path

from config import DB_PATH


def get_connection():
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS news_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            title TEXT NOT NULL,
            press TEXT,
            link TEXT UNIQUE,
            content TEXT,
            content_length INTEGER,
            crawled_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()


def save_articles_to_db(articles):
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    saved_count = 0
    skipped_count = 0

    for article in articles:
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO news_articles (
                    section,
                    title,
                    press,
                    link,
                    content,
                    content_length,
                    crawled_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.get("section", ""),
                    article.get("title", ""),
                    article.get("press", ""),
                    article.get("link", ""),
                    article.get("content", ""),
                    article.get("content_length", len(article.get("content", ""))),
                    article.get("crawled_at", ""),
                ),
            )

            if cursor.rowcount == 1:
                saved_count += 1
            else:
                skipped_count += 1

        except Exception as e:
            print(f"[DB 저장 실패] {article.get('title', '')} / {e}")

    conn.commit()
    conn.close()

    return saved_count, skipped_count


def get_article_count():
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM news_articles")
    count = cursor.fetchone()[0]

    conn.close()
    return count

def search_articles(keyword="", section="전체", limit=50):
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            section,
            title,
            press,
            link,
            content,
            crawled_at
        FROM news_articles
        WHERE 1=1
    """

    params = []

    if keyword:
        query += """
            AND (
                title LIKE ?
                OR content LIKE ?
                OR press LIKE ?
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword])

    if section != "전체":
        query += " AND section = ?"
        params.append(section)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    conn.close()

    articles = []

    for row in rows:
        articles.append(
            {
                "section": row[0],
                "title": row[1],
                "press": row[2],
                "link": row[3],
                "content": row[4],
                "crawled_at": row[5],
            }
        )

    return articles