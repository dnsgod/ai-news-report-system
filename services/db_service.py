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