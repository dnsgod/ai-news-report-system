import sqlite3
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL_NAME
from services.db_service import get_connection


@lru_cache(maxsize=1)
def get_embedding_model():
    """
    임베딩 모델을 최초 한 번만 불러온다.

    Streamlit이나 다른 코드에서 여러 번 호출해도
    매번 모델을 다시 로드하지 않도록 캐시한다.
    """

    print(
        "[Embedding] 모델 로드 중: "
        f"{EMBEDDING_MODEL_NAME}"
    )

    return SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )


def init_embedding_table():
    """
    기사 임베딩을 저장할 테이블을 생성한다.

    article_id는 news_articles 테이블의 기사 ID와 연결된다.
    embedding에는 NumPy 벡터를 BLOB 형식으로 저장한다.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS article_embeddings (
            article_id INTEGER PRIMARY KEY,
            embedding BLOB NOT NULL,
            dimension INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (article_id)
            REFERENCES news_articles(id)
            ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()


def build_article_text(
    title,
    content,
    section="",
    tags="",
):
    """
    임베딩으로 변환할 기사 문자열을 만든다.

    제목에는 중요한 정보가 많기 때문에 제목을 먼저 넣고,
    섹션, 태그, 본문 일부를 함께 사용한다.
    """

    title = title or ""
    content = content or ""
    section = section or ""
    tags = tags or ""

    content = content.replace(
        "\n",
        " ",
    ).strip()

    # 지나치게 긴 기사로 인한 처리 시간 증가를 줄인다.
    content = content[:2500]

    return (
        f"섹션: {section}\n"
        f"태그: {tags}\n"
        f"제목: {title}\n"
        f"본문: {content}"
    )


def create_embedding(text):
    """
    문자열 하나를 임베딩 벡터로 변환한다.

    normalize_embeddings=True를 사용하여
    벡터 길이를 1로 정규화한다.
    """

    model = get_embedding_model()

    embedding = model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    return embedding.astype(
        np.float32
    )


def vector_to_blob(vector):
    """
    NumPy 벡터를 SQLite BLOB으로 변환한다.
    """

    return vector.astype(
        np.float32
    ).tobytes()


def blob_to_vector(blob, dimension):
    """
    SQLite BLOB을 다시 NumPy 벡터로 복원한다.
    """

    vector = np.frombuffer(
        blob,
        dtype=np.float32,
    )

    if len(vector) != dimension:
        raise ValueError(
            "저장된 임베딩 차원과 "
            "실제 벡터 길이가 일치하지 않습니다."
        )

    return vector


def get_articles_without_embeddings(
    limit=None,
):
    """
    아직 임베딩이 만들어지지 않은 기사만 조회한다.
    """

    init_embedding_table()

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    query = """
        SELECT
            n.id,
            n.section,
            n.title,
            n.content,
            n.tags
        FROM news_articles AS n

        LEFT JOIN article_embeddings AS e
            ON n.id = e.article_id

        WHERE e.article_id IS NULL

        ORDER BY n.id ASC
    """

    params = []

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(
        query,
        params,
    )

    rows = cursor.fetchall()
    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def save_article_embedding(
    article_id,
    embedding,
):
    """
    생성된 기사 임베딩을 SQLite에 저장한다.
    """

    init_embedding_table()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO article_embeddings (
            article_id,
            embedding,
            dimension,
            model_name
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            article_id,
            vector_to_blob(embedding),
            len(embedding),
            EMBEDDING_MODEL_NAME,
        ),
    )

    conn.commit()
    conn.close()


def create_missing_embeddings(
    limit=None,
):
    """
    아직 벡터가 없는 기사들의 임베딩을 생성한다.
    """

    articles = get_articles_without_embeddings(
        limit=limit
    )

    if not articles:
        print(
            "[Embedding] 새로 생성할 "
            "기사 임베딩이 없습니다."
        )

        return {
            "created": 0,
            "failed": 0,
        }

    created_count = 0
    failed_count = 0

    total_count = len(articles)

    for index, article in enumerate(
        articles,
        start=1,
    ):
        article_id = article["id"]
        title = article.get(
            "title",
            "",
        )

        print(
            f"[Embedding] "
            f"{index}/{total_count} "
            f"{title[:40]}..."
        )

        try:
            article_text = build_article_text(
                title=article.get(
                    "title",
                    "",
                ),
                content=article.get(
                    "content",
                    "",
                ),
                section=article.get(
                    "section",
                    "",
                ),
                tags=article.get(
                    "tags",
                    "",
                ),
            )

            embedding = create_embedding(
                article_text
            )

            save_article_embedding(
                article_id=article_id,
                embedding=embedding,
            )

            created_count += 1

        except Exception as error:
            failed_count += 1

            print(
                f"[Embedding 실패] "
                f"{title} / {error}"
            )

    return {
        "created": created_count,
        "failed": failed_count,
    }


def get_all_embedded_articles():
    """
    임베딩이 저장된 기사와 벡터를 함께 조회한다.
    """

    init_embedding_table()

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            n.id,
            n.section,
            n.title,
            n.press,
            n.link,
            n.content,
            n.crawled_at,
            n.sentiment,
            n.tags,
            e.embedding,
            e.dimension

        FROM news_articles AS n

        INNER JOIN article_embeddings AS e
            ON n.id = e.article_id
        """
    )

    rows = cursor.fetchall()
    conn.close()

    articles = []

    for row in rows:
        article = dict(row)

        article["embedding"] = (
            blob_to_vector(
                article["embedding"],
                article["dimension"],
            )
        )

        articles.append(article)

    return articles


def cosine_similarity(
    vector_a,
    vector_b,
):
    """
    두 벡터의 코사인 유사도를 계산한다.

    임베딩 생성 시 이미 정규화했으므로
    내적만 계산해도 코사인 유사도가 된다.
    """

    return float(
        np.dot(
            vector_a,
            vector_b,
        )
    )


def search_similar_articles(
    query,
    top_n=5,
    min_score=0.25,
):
    """
    질문과 의미가 가까운 기사를 벡터 유사도로 검색한다.
    """

    if not query.strip():
        return []

    query_embedding = create_embedding(
        query
    )

    articles = get_all_embedded_articles()

    results = []

    for article in articles:
        score = cosine_similarity(
            query_embedding,
            article["embedding"],
        )

        if score < min_score:
            continue

        article.pop(
            "embedding",
            None,
        )

        article.pop(
            "dimension",
            None,
        )

        article["vector_score"] = score

        results.append(article)

    results.sort(
        key=lambda item: item["vector_score"],
        reverse=True,
    )

    return results[:top_n]