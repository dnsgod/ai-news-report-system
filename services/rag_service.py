import re

from services.db_service import search_articles
from services.llm_service import call_ollama
from services.vector_service import search_similar_articles


QUESTION_STOPWORDS = {
    "오늘",
    "최근",
    "뉴스",
    "기사",
    "관련",
    "대해",
    "대한",
    "알려줘",
    "보여줘",
    "정리해줘",
    "요약해줘",
    "설명해줘",
    "어때",
    "어떤",
    "무슨",
    "있는",
    "있어",
    "있나요",
    "해줘",
    "인가",
    "이슈",
}


def clean_keyword(keyword):
    """
    LLM이 반환한 키워드에서 번호, 따옴표,
    괄호 및 불필요한 기호를 제거한다.
    """

    keyword = keyword.strip()

    keyword = re.sub(
        r"^[\-\*\d\.\)\s]+",
        "",
        keyword,
    )

    keyword = keyword.replace('"', "")
    keyword = keyword.replace("'", "")
    keyword = keyword.replace("[", "")
    keyword = keyword.replace("]", "")
    keyword = keyword.strip()

    return keyword


def fallback_extract_keywords(
    question,
    max_keywords=5,
):
    """
    Ollama 키워드 추출에 실패했을 때 사용하는
    규칙 기반 키워드 추출 방식이다.
    """

    words = re.findall(
        r"[가-힣A-Za-z0-9]{2,}",
        question,
    )

    keywords = []

    for word in words:
        if word in QUESTION_STOPWORDS:
            continue

        if word not in keywords:
            keywords.append(word)

        if len(keywords) >= max_keywords:
            break

    return keywords


def extract_question_keywords(
    question,
    max_keywords=5,
):
    """
    질문에서 SQLite 키워드 검색에 사용할
    핵심 검색어를 추출한다.
    """

    if not question.strip():
        return []

    prompt = f"""
다음 사용자 질문에서 뉴스 검색에 사용할 핵심 키워드를 추출해라.

조건:
- 최대 {max_keywords}개
- 뉴스 검색에 도움이 되는 명사 위주
- '뉴스', '기사', '오늘', '요약', '알려줘' 같은 표현은 제외
- 쉼표로만 구분
- 설명이나 문장은 작성하지 말 것

예시:

질문:
오늘 반도체 시장 전망을 요약해줘

출력:
반도체, 시장, 전망

질문:
최근 삼성전자와 SK하이닉스 관련 소식을 비교해줘

출력:
삼성전자, SK하이닉스

사용자 질문:
{question}
"""

    try:
        response = call_ollama(
            prompt,
            timeout=120,
        )

        raw_keywords = re.split(
            r"[,،\n]",
            response,
        )

        keywords = []

        for raw_keyword in raw_keywords:
            keyword = clean_keyword(raw_keyword)

            if not keyword:
                continue

            if keyword in QUESTION_STOPWORDS:
                continue

            if len(keyword) < 2:
                continue

            if keyword not in keywords:
                keywords.append(keyword)

            if len(keywords) >= max_keywords:
                break

        if keywords:
            return keywords

    except Exception as error:
        print(
            f"[질문 키워드 추출 실패] {error}"
        )

    return fallback_extract_keywords(
        question=question,
        max_keywords=max_keywords,
    )


def calculate_keyword_score(
    article,
    keywords,
):
    """
    기사에서 질문 키워드가 발견된 위치에 따라
    키워드 관련도 점수를 계산한다.

    제목: 5점
    태그: 3점
    본문: 2점
    언론사: 1점
    """

    title = (
        article.get("title") or ""
    ).lower()

    content = (
        article.get("content") or ""
    ).lower()

    tags = (
        article.get("tags") or ""
    ).lower()

    press = (
        article.get("press") or ""
    ).lower()

    score = 0

    for keyword in keywords:
        normalized_keyword = (
            keyword or ""
        ).lower().strip()

        if not normalized_keyword:
            continue

        if normalized_keyword in title:
            score += 5

        if normalized_keyword in tags:
            score += 3

        if normalized_keyword in content:
            score += 2

        if normalized_keyword in press:
            score += 1

    return score


def search_articles_by_keywords(
    keywords,
    candidate_limit=30,
):
    """
    여러 키워드로 SQLite LIKE 검색을 수행한다.

    기사 링크 또는 제목을 기준으로 중복을 제거하고,
    키워드 점수를 계산한다.
    """

    article_map = {}

    per_keyword_limit = max(
        candidate_limit,
        10,
    )

    for keyword in keywords:
        results = search_articles(
            keyword=keyword,
            section="전체",
            press="전체",
            tag="전체",
            sentiment="전체",
            start_date=None,
            end_date=None,
            limit=per_keyword_limit,
        )

        for article in results:
            link = article.get("link") or ""
            title = article.get("title") or ""

            unique_key = link or title

            if not unique_key:
                continue

            if unique_key not in article_map:
                article_map[unique_key] = dict(article)

    articles = list(article_map.values())

    for article in articles:
        article["keyword_score"] = (
            calculate_keyword_score(
                article=article,
                keywords=keywords,
            )
        )

    articles.sort(
        key=lambda item: item.get(
            "keyword_score",
            0,
        ),
        reverse=True,
    )

    return articles[:candidate_limit]


def normalize_keyword_scores(
    articles,
):
    """
    키워드 점수를 0~1 사이 값으로 정규화한다.
    """

    if not articles:
        return articles

    max_score = max(
        article.get("keyword_score", 0)
        for article in articles
    )

    for article in articles:
        raw_score = article.get(
            "keyword_score",
            0,
        )

        if max_score > 0:
            article["normalized_keyword_score"] = (
                raw_score / max_score
            )
        else:
            article["normalized_keyword_score"] = 0.0

    return articles


def normalize_vector_scores(
    articles,
):
    """
    벡터 유사도 점수를 0~1 사이 값으로 보정한다.

    코사인 유사도는 이미 대체로 0~1 범위이지만,
    음수나 1 초과 값이 들어오지 않도록 제한한다.
    """

    for article in articles:
        raw_score = article.get(
            "vector_score",
            0.0,
        )

        normalized_score = max(
            0.0,
            min(float(raw_score), 1.0),
        )

        article["normalized_vector_score"] = (
            normalized_score
        )

    return articles


def merge_hybrid_results(
    keyword_articles,
    vector_articles,
    top_n=5,
    keyword_weight=0.45,
    vector_weight=0.55,
):
    """
    키워드 검색 결과와 벡터 검색 결과를 통합한다.

    같은 기사는 링크 또는 제목을 기준으로 중복 제거한다.

    기본 가중치:
    - 키워드 검색: 45%
    - 벡터 검색: 55%
    """

    merged = {}

    for article in keyword_articles:
        link = article.get("link") or ""
        title = article.get("title") or ""
        unique_key = link or title

        if not unique_key:
            continue

        merged[unique_key] = dict(article)

        merged[unique_key].setdefault(
            "normalized_keyword_score",
            0.0,
        )
        merged[unique_key].setdefault(
            "normalized_vector_score",
            0.0,
        )

        merged[unique_key]["found_by_keyword"] = True
        merged[unique_key]["found_by_vector"] = False

    for article in vector_articles:
        link = article.get("link") or ""
        title = article.get("title") or ""
        unique_key = link or title

        if not unique_key:
            continue

        if unique_key not in merged:
            merged[unique_key] = dict(article)

            merged[unique_key].setdefault(
                "normalized_keyword_score",
                0.0,
            )
            merged[unique_key]["found_by_keyword"] = False

        merged[unique_key][
            "normalized_vector_score"
        ] = article.get(
            "normalized_vector_score",
            0.0,
        )

        merged[unique_key][
            "vector_score"
        ] = article.get(
            "vector_score",
            0.0,
        )

        merged[unique_key]["found_by_vector"] = True

    final_articles = list(
        merged.values()
    )

    for article in final_articles:
        keyword_score = article.get(
            "normalized_keyword_score",
            0.0,
        )

        vector_score = article.get(
            "normalized_vector_score",
            0.0,
        )

        hybrid_score = (
            keyword_score * keyword_weight
            + vector_score * vector_weight
        )

        # 두 검색 방식에서 동시에 발견되면 소폭 가산점
        if (
            article.get("found_by_keyword")
            and article.get("found_by_vector")
        ):
            hybrid_score += 0.05

        article["hybrid_score"] = min(
            hybrid_score,
            1.0,
        )

        if (
            article.get("found_by_keyword")
            and article.get("found_by_vector")
        ):
            article["retrieval_source"] = (
                "키워드 + 벡터"
            )
        elif article.get("found_by_vector"):
            article["retrieval_source"] = (
                "벡터"
            )
        else:
            article["retrieval_source"] = (
                "키워드"
            )

    final_articles.sort(
        key=lambda item: item.get(
            "hybrid_score",
            0.0,
        ),
        reverse=True,
    )

    return final_articles[:top_n]


def hybrid_search_articles(
    question,
    keywords,
    top_n=5,
):
    """
    키워드 검색과 벡터 검색을 동시에 실행하고
    결과를 통합하여 상위 기사를 반환한다.
    """

    candidate_limit = max(
        top_n * 4,
        20,
    )

    keyword_articles = (
        search_articles_by_keywords(
            keywords=keywords,
            candidate_limit=candidate_limit,
        )
    )

    keyword_articles = (
        normalize_keyword_scores(
            keyword_articles
        )
    )

    try:
        vector_articles = (
            search_similar_articles(
                query=question,
                top_n=candidate_limit,
                min_score=0.20,
            )
        )

    except Exception as error:
        print(
            f"[벡터 검색 실패] {error}"
        )
        vector_articles = []

    vector_articles = normalize_vector_scores(
        vector_articles
    )

    return merge_hybrid_results(
        keyword_articles=keyword_articles,
        vector_articles=vector_articles,
        top_n=top_n,
        keyword_weight=0.45,
        vector_weight=0.55,
    )


def build_context_from_articles(
    articles,
    max_articles=5,
):
    """
    검색된 기사들을 Ollama가 읽을 수 있는
    문맥 문자열로 변환한다.
    """

    selected_articles = articles[
        :max_articles
    ]

    context_parts = []

    for index, article in enumerate(
        selected_articles,
        start=1,
    ):
        title = article.get(
            "title"
        ) or ""

        press = article.get(
            "press"
        ) or ""

        section = article.get(
            "section"
        ) or ""

        content = article.get(
            "content"
        ) or ""

        link = article.get(
            "link"
        ) or ""

        sentiment = article.get(
            "sentiment"
        ) or ""

        tags = article.get(
            "tags"
        ) or ""

        hybrid_score = article.get(
            "hybrid_score",
            0.0,
        )

        retrieval_source = article.get(
            "retrieval_source",
            "",
        )

        content = content.replace(
            "\n",
            " ",
        ).strip()

        content = content[:1500]

        context_parts.append(
            f"""
[기사 {index}]
섹션: {section}
언론사: {press}
제목: {title}
분위기: {sentiment}
태그: {tags}
검색 방식: {retrieval_source}
하이브리드 점수: {hybrid_score:.4f}
본문: {content}
링크: {link}
"""
        )

    return "\n".join(context_parts)


def answer_news_question(
    question,
    limit=5,
):
    """
    질문 분석부터 하이브리드 검색,
    근거 기반 답변 생성까지 수행한다.
    """

    if not question.strip():
        return {
            "answer": "질문을 입력해주세요.",
            "articles": [],
            "keywords": [],
            "search_type": "hybrid",
        }

    keywords = extract_question_keywords(
        question=question,
        max_keywords=5,
    )

    if not keywords:
        return {
            "answer": (
                "질문에서 검색 키워드를 "
                "추출하지 못했습니다."
            ),
            "articles": [],
            "keywords": [],
            "search_type": "hybrid",
        }

    articles = hybrid_search_articles(
        question=question,
        keywords=keywords,
        top_n=limit,
    )

    if not articles:
        keyword_text = ", ".join(
            keywords
        )

        return {
            "answer": (
                f"추출된 키워드는 "
                f"'{keyword_text}'이지만 "
                "관련 뉴스를 찾지 못했습니다."
            ),
            "articles": [],
            "keywords": keywords,
            "search_type": "hybrid",
        }

    context = build_context_from_articles(
        articles=articles,
        max_articles=limit,
    )

    keyword_text = ", ".join(
        keywords
    )

    prompt = f"""
너는 뉴스 분석 비서다.

아래에 제공된 뉴스 기사만 근거로 사용자의 질문에 답변해라.
기사에 없는 내용은 추측하거나 사실처럼 말하지 마라.

사용자의 질문:
{question}

검색에 사용한 핵심 키워드:
{keyword_text}

검색 방식:
키워드 검색과 의미 기반 벡터 검색을 결합한 하이브리드 검색

답변 조건:
- 한국어로 답변
- 가장 중요한 결론부터 제시
- 기사들의 공통 내용과 차이점을 구분
- 불확실한 내용은 불확실하다고 표시
- 기사에 없는 정보는 추가하지 말 것
- 마지막에 '참고 기사' 항목으로 제목을 나열
- 지나치게 길지 않게 작성

검색된 뉴스 기사:
{context}
"""

    try:
        answer = call_ollama(
            prompt,
            timeout=240,
        )

    except Exception as error:
        print(
            f"[뉴스 질문 답변 실패] "
            f"{error}"
        )

        answer = (
            "뉴스 질문 답변 생성에 "
            "실패했습니다."
        )

    return {
        "answer": answer,
        "articles": articles,
        "keywords": keywords,
        "search_type": "hybrid",
    }