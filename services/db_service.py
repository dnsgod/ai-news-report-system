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

def search_articles(
    keyword="",
    section="전체",
    press="전체",
    start_date=None,
    end_date=None,
    limit=50,
):
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

    if press != "전체":
        query += " AND press = ?"
        params.append(press)

    if start_date:
        query += " AND substr(crawled_at, 1, 10) >= ?"
        params.append(str(start_date))

    if end_date:
        query += " AND substr(crawled_at, 1, 10) <= ?"
        params.append(str(end_date))

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

def get_press_list():
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT press
        FROM news_articles
        WHERE press IS NOT NULL
          AND press != ''
        ORDER BY press
        """
    )

    rows = cursor.fetchall()
    conn.close()

    press_list = [row[0] for row in rows]

    return press_list

def get_press_statistics(limit=10):
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT press, COUNT(*) AS count
        FROM news_articles
        WHERE press IS NOT NULL
          AND press != ''
        GROUP BY press
        ORDER BY count DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "press": row[0],
            "count": row[1],
        }
        for row in rows
    ]


def get_section_statistics():
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT section, COUNT(*) AS count
        FROM news_articles
        WHERE section IS NOT NULL
          AND section != ''
        GROUP BY section
        ORDER BY count DESC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "section": row[0],
            "count": row[1],
        }
        for row in rows
    ]


def get_daily_statistics(limit=14):
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT substr(crawled_at, 1, 10) AS date, COUNT(*) AS count
        FROM news_articles
        WHERE crawled_at IS NOT NULL
          AND crawled_at != ''
        GROUP BY substr(crawled_at, 1, 10)
        ORDER BY date DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    rows = list(reversed(rows))

    return [
        {
            "date": row[0],
            "count": row[1],
        }
        for row in rows
    ]