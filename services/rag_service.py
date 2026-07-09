from services.db_service import search_articles
from services.llm_service import call_ollama


def build_context_from_articles(articles, max_articles=5):
    """
    검색된 기사 목록을 LLM에게 전달할 context 문자열로 만든다.
    """

    selected_articles = articles[:max_articles]

    context_parts = []

    for idx, article in enumerate(selected_articles, start=1):
        title = article.get("title", "")
        press = article.get("press", "")
        section = article.get("section", "")
        content = article.get("content", "")
        link = article.get("link", "")

        content = content.replace("\n", " ").strip()
        content = content[:1200]

        context_parts.append(
            f"""
[기사 {idx}]
섹션: {section}
언론사: {press}
제목: {title}
본문: {content}
링크: {link}
"""
        )

    return "\n".join(context_parts)


def answer_news_question(question, limit=5):
    """
    사용자 질문을 기반으로 SQLite에서 관련 기사를 검색하고,
    검색된 기사들을 근거로 LLM 답변을 생성한다.
    """

    if not question.strip():
        return {
            "answer": "질문을 입력해주세요.",
            "articles": [],
        }

    articles = search_articles(
        keyword=question,
        section="전체",
        press="전체",
        tag="전체",
        sentiment="전체",
        limit=limit,
    )

    if not articles:
        return {
            "answer": "관련 뉴스를 찾지 못했습니다.",
            "articles": [],
        }

    context = build_context_from_articles(articles, max_articles=limit)

    prompt = f"""
너는 뉴스 분석 비서다.

아래 제공된 뉴스 기사 내용만 근거로 사용자의 질문에 답변해라.
기사에 없는 내용은 추측하지 마라.

답변 조건:
- 한국어로 답변
- 핵심 내용을 먼저 요약
- 관련 기사들의 공통점이나 차이가 있으면 설명
- 마지막에 참고한 기사 제목을 간단히 나열

사용자 질문:
{question}

뉴스 기사:
{context}
"""

    try:
        answer = call_ollama(prompt, timeout=180)

    except Exception as e:
        print(f"[뉴스 질문 답변 실패] {e}")
        answer = "뉴스 질문 답변 생성에 실패했습니다."

    return {
        "answer": answer,
        "articles": articles,
    }