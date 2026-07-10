import re

from services.db_service import search_articles
from services.llm_service import call_ollama


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
    LLM이 반환한 키워드에서 번호, 따옴표, 기호 등을 제거한다.
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


def fallback_extract_keywords(question, max_keywords=5):
    """
    Ollama 키워드 추출에 실패했을 때 사용하는 단순 규칙 기반 방식이다.
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


def extract_question_keywords(question, max_keywords=5):
    """
    사용자 질문을 Ollama에 전달하여 검색에 사용할 핵심 키워드를 추출한다.
    """

    if not question.strip():
        return []

    prompt = f"""
다음 사용자 질문에서 뉴스 검색에 사용할 핵심 키워드를 추출해라.

조건:
- 최대 {max_keywords}개
- 뉴스 검색에 실제로 도움이 되는 명사 위주
- '뉴스', '기사', '오늘', '요약', '알려줘' 같은 일반적인 표현은 제외
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

    except Exception as e:
        print(f"[질문 키워드 추출 실패] {e}")

    return fallback_extract_keywords(
        question,
        max_keywords=max_keywords,
    )


def calculate_article_relevance(article, keywords):
    """
    검색된 기사가 질문 키워드를 얼마나 많이 포함하는지 계산한다.

    제목에 포함된 키워드는 본문보다 높은 점수를 준다.
    None 값도 안전하게 처리한다.
    """

    title = (article.get("title") or "").lower()
    content = (article.get("content") or "").lower()
    tags = (article.get("tags") or "").lower()
    press = (article.get("press") or "").lower()

    score = 0

    for keyword in keywords:
        keyword = (keyword or "").lower().strip()

        if not keyword:
            continue

        if keyword in title:
            score += 5

        if keyword in tags:
            score += 3

        if keyword in content:
            score += 2

        if keyword in press:
            score += 1

    return score


def search_articles_by_keywords(keywords, limit=5):
    """
    각 키워드로 SQLite 검색을 수행하고,
    중복 기사를 제거한 뒤 관련도 점수 순으로 정렬한다.
    """

    article_map = {}

    search_limit_per_keyword = max(
        limit * 3,
        10,
    )

    for keyword in keywords:
        results = search_articles(
            keyword=keyword,
            section="전체",
            press="전체",
            tag="전체",
            sentiment="전체",
            limit=search_limit_per_keyword,
        )

        for article in results:
            link = article.get("link", "")
            title = article.get("title", "")

            unique_key = link or title

            if not unique_key:
                continue

            if unique_key not in article_map:
                article_map[unique_key] = article

    articles = list(article_map.values())

    for article in articles:
        article["relevance_score"] = calculate_article_relevance(
            article,
            keywords,
        )

    articles.sort(
        key=lambda article: article.get(
            "relevance_score",
            0,
        ),
        reverse=True,
    )

    return articles[:limit]


def build_context_from_articles(articles, max_articles=5):
    """
    검색된 기사들을 Ollama에 전달할 문맥 문자열로 만든다.
    """

    selected_articles = articles[:max_articles]
    context_parts = []

    for idx, article in enumerate(
        selected_articles,
        start=1,
    ):
        title = article.get("title", "")
        press = article.get("press", "")
        section = article.get("section", "")
        content = article.get("content", "")
        link = article.get("link", "")
        sentiment = article.get("sentiment", "")
        tags = article.get("tags", "")

        content = content.replace(
            "\n",
            " ",
        ).strip()

        content = content[:1500]

        context_parts.append(
            f"""
[기사 {idx}]
섹션: {section}
언론사: {press}
제목: {title}
분위기: {sentiment}
태그: {tags}
본문: {content}
링크: {link}
"""
        )

    return "\n".join(context_parts)


def answer_news_question(question, limit=5):
    """
    질문에서 핵심 키워드를 추출하고,
    관련 기사를 검색한 뒤 Ollama가 근거 기반 답변을 생성한다.
    """

    if not question.strip():
        return {
            "answer": "질문을 입력해주세요.",
            "articles": [],
            "keywords": [],
        }

    keywords = extract_question_keywords(
        question,
        max_keywords=5,
    )

    if not keywords:
        return {
            "answer": "질문에서 검색 키워드를 추출하지 못했습니다.",
            "articles": [],
            "keywords": [],
        }

    articles = search_articles_by_keywords(
        keywords,
        limit=limit,
    )

    if not articles:
        keyword_text = ", ".join(keywords)

        return {
            "answer": (
                f"추출된 키워드는 '{keyword_text}'이지만 "
                "관련 뉴스를 찾지 못했습니다."
            ),
            "articles": [],
            "keywords": keywords,
        }

    context = build_context_from_articles(
        articles,
        max_articles=limit,
    )

    keyword_text = ", ".join(keywords)

    prompt = f"""
너는 뉴스 분석 비서다.

아래에 제공된 뉴스 기사만 근거로 사용자의 질문에 답변해라.
기사에 없는 내용은 추측하거나 사실처럼 말하지 마라.

사용자가 질문한 내용:
{question}

검색에 사용한 키워드:
{keyword_text}

답변 조건:
- 한국어로 답변
- 가장 중요한 결론부터 제시
- 기사들의 공통 내용과 차이점을 구분
- 불확실한 내용은 불확실하다고 표시
- 참고 기사에 없는 정보는 추가하지 말 것
- 마지막에 '참고 기사' 항목으로 기사 제목을 나열
- 지나치게 길지 않게 작성

검색된 뉴스 기사:
{context}
"""

    try:
        answer = call_ollama(
            prompt,
            timeout=240,
        )

    except Exception as e:
        print(f"[뉴스 질문 답변 실패] {e}")
        answer = "뉴스 질문 답변 생성에 실패했습니다."

    return {
        "answer": answer,
        "articles": articles,
        "keywords": keywords,
    }