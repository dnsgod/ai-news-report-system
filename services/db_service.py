import sqlite3
from pathlib import Path

from config import DB_PATH
from services.sentiment_service import analyze_sentiment
from services.tag_service import assign_tags


def get_connection():
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


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

    cursor.execute("PRAGMA table_info(news_articles)")
    columns = [row[1] for row in cursor.fetchall()]

    if "sentiment" not in columns:
        cursor.execute("ALTER TABLE news_articles ADD COLUMN sentiment TEXT")

    if "tags" not in columns:
        cursor.execute("ALTER TABLE news_articles ADD COLUMN tags TEXT")

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
            title = article.get("title", "")
            content = article.get("content", "")

            sentiment = analyze_sentiment(title, content)
            tags = assign_tags(title, content)
            tag_text = ",".join(tags)

            cursor.execute(
                """
                INSERT OR IGNORE INTO news_articles (
                    section,
                    title,
                    press,
                    link,
                    content,
                    content_length,
                    crawled_at,
                    sentiment,
                    tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.get("section", ""),
                    title,
                    article.get("press", ""),
                    article.get("link", ""),
                    content,
                    article.get("content_length", len(content)),
                    article.get("crawled_at", ""),
                    sentiment,
                    tag_text,
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
    tag="전체",
    sentiment="전체",
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
            crawled_at,
            sentiment,
            tags
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
                OR tags LIKE ?
                OR sentiment LIKE ?
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([
            like_keyword,
            like_keyword,
            like_keyword,
            like_keyword,
            like_keyword,
        ])

    if section != "전체":
        query += " AND section = ?"
        params.append(section)

    if press != "전체":
        query += " AND press = ?"
        params.append(press)

    if tag != "전체":
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")

    if sentiment != "전체":
        query += " AND sentiment = ?"
        params.append(sentiment)

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

    return [
        {
            "section": row[0],
            "title": row[1],
            "press": row[2],
            "link": row[3],
            "content": row[4],
            "crawled_at": row[5],
            "sentiment": row[6],
            "tags": row[7],
        }
        for row in rows
    ]


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

    return [row[0] for row in rows]


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

    return [{"press": row[0], "count": row[1]} for row in rows]


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

    return [{"section": row[0], "count": row[1]} for row in rows]


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

    return [{"date": row[0], "count": row[1]} for row in rows]

def get_tag_list():
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT tags
        FROM news_articles
        WHERE tags IS NOT NULL
          AND tags != ''
        """
    )

    rows = cursor.fetchall()
    conn.close()

    tag_set = set()

    for row in rows:
        tag_text = row[0]

        for tag in tag_text.split(","):
            tag = tag.strip()

            if tag:
                tag_set.add(tag)

    return sorted(tag_set)

def get_sentiment_statistics():
    """
    SQLite에 저장된 뉴스의 감정 분석 결과를 집계한다.
    """

    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT sentiment, COUNT(*) AS count
        FROM news_articles
        WHERE sentiment IS NOT NULL
          AND sentiment != ''
        GROUP BY sentiment
        ORDER BY count DESC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    sentiment_counts = {
        "긍정": 0,
        "중립": 0,
        "부정": 0,
    }

    for sentiment, count in rows:
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] = count

    total = sum(sentiment_counts.values())

    results = []

    for sentiment in ["긍정", "중립", "부정"]:
        count = sentiment_counts[sentiment]

        if total > 0:
            percentage = count / total * 100
        else:
            percentage = 0.0

        results.append(
            {
                "sentiment": sentiment,
                "count": count,
                "percentage": percentage,
            }
        )

    return results