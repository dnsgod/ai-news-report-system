import time

from services.hot_news_service import get_hot_articles
from services.keyword_service import extract_keywords
from services.llm_service import local_llm_summary, summarize_section
from services.sentiment_service import analyze_sentiment, analyze_section_sentiment
from services.tag_service import assign_tags
from services.trend_service import get_recent_keywords, get_rising_keywords
from utils.file_utils import save_report


def append_recent_keywords(lines):
    recent_keywords = get_recent_keywords(days=3, top_n=10)

    lines.append("## 🔁 최근 3일 반복 키워드")
    lines.append("")

    if recent_keywords:
        keyword_text = ", ".join([word for word, count in recent_keywords])
        lines.append(keyword_text)
    else:
        lines.append("최근 키워드를 추출하지 못했습니다.")

    lines.append("")
    lines.append("---")
    lines.append("")


def append_rising_keywords(lines, today_articles):
    rising_keywords = get_rising_keywords(today_articles, days=3, top_n=10)

    lines.append("## 📈 급상승 키워드")
    lines.append("")

    if rising_keywords:
        for word, today_count, recent_count, score in rising_keywords:
            lines.append(
                f"- {word} "
                f"(오늘 {today_count}회 / 최근 {recent_count}회 / 점수 {score:.2f})"
            )
    else:
        lines.append("급상승 키워드를 찾지 못했습니다.")

    lines.append("")
    lines.append("---")
    lines.append("")

    return rising_keywords


def append_hot_articles(lines, today_articles, rising_keywords):
    hot_articles = get_hot_articles(
        today_articles,
        rising_keywords,
        top_n=5,
    )

    lines.append("## 🔥 오늘의 핵심 뉴스")
    lines.append("")

    if not hot_articles:
        lines.append("핵심 뉴스를 선정하지 못했습니다.")
        lines.append("")
        lines.append("---")
        lines.append("")
        return

    for idx, article in enumerate(hot_articles, start=1):
        tag_text = ", ".join(article.get("tags", ["기타"]))

        lines.append(
            f"{idx}. {article['title']} "
            f"(점수: {article['score']})"
        )
        lines.append(f"   - 언론사: {article['press']}")
        lines.append(f"   - 태그: {tag_text}")
        lines.append(f"   - 링크: {article['link']}")
        lines.append("")

    lines.append("---")
    lines.append("")


def append_sentiment_report(lines, sentiment_result):
    total = sum(sentiment_result.values())

    lines.append("**섹션 분위기 분석**")
    lines.append("")

    if total == 0:
        lines.append("분위기 분석 결과가 없습니다.")
        lines.append("")
        return

    positive = sentiment_result["긍정"]
    neutral = sentiment_result["중립"]
    negative = sentiment_result["부정"]

    lines.append(f"- 긍정: {positive}건")
    lines.append(f"- 중립: {neutral}건")
    lines.append(f"- 부정: {negative}건")
    lines.append("")

    if negative >= positive and negative >= neutral:
        lines.append("전체적으로 부정적 이슈의 비중이 높은 섹션입니다.")
    elif positive >= negative and positive >= neutral:
        lines.append("전체적으로 긍정적 이슈의 비중이 높은 섹션입니다.")
    else:
        lines.append("전체적으로 중립적 정보 전달 성격이 강한 섹션입니다.")

    lines.append("")


def append_section_report(lines, section, articles):
    lines.append(f"## 📌 {section}")
    lines.append("")

    keywords = extract_keywords(articles, top_n=8)

    lines.append("**핵심 키워드**")
    lines.append("")

    if keywords:
        keyword_text = ", ".join([word for word, count in keywords])
        lines.append(keyword_text)
    else:
        lines.append("키워드를 추출하지 못했습니다.")

    lines.append("")

    print(f"[섹션 요약 중] {section}")
    section_summary = summarize_section(section, articles)

    lines.append("**섹션 핵심 흐름**")
    lines.append("")
    lines.append(section_summary)
    lines.append("")
    lines.append("---")
    lines.append("")

    sentiment_result = analyze_section_sentiment(articles)
    append_sentiment_report(lines, sentiment_result)

    lines.append("---")
    lines.append("")

    for idx, article in enumerate(articles, start=1):
        title = article.get("title", "제목 없음")
        press = article.get("press") or "언론사 미확인"
        link = article.get("link", "")
        content = article.get("content", "")

        print(f"[요약 중] {section} - {title[:40]}...")

        summary = local_llm_summary(title, content)
        sentiment = analyze_sentiment(title, content)
        tags = assign_tags(title, content)
        tag_text = ", ".join(tags)

        lines.append(f"### {idx}. {title}")
        lines.append("")
        lines.append(f"- 언론사: {press}")
        lines.append(f"- 태그: {tag_text}")
        lines.append(f"- 분위기: {sentiment}")
        lines.append(f"- 링크: {link}")
        lines.append("")
        lines.append("**AI 요약**")
        lines.append("")
        lines.append(summary)
        lines.append("")
        lines.append("---")
        lines.append("")

        time.sleep(0.3)


def create_markdown_report(grouped_articles, date_str, original_count, removed_count):
    lines = []

    lines.append("# 📰 네이버 뉴스 아침 리포트")
    lines.append("")
    lines.append(f"- 생성 날짜: {date_str}")
    lines.append("- 기준: 네이버 뉴스 섹션별 헤드라인")
    lines.append("- 요약 방식: Ollama 로컬 LLM")
    lines.append(
        "- 분석 기능: 키워드 추출, 섹션 요약, 유사 기사 제거, "
        "최근 반복 키워드, 급상승 키워드, 분위기 분석, 자동 태깅, 핵심 뉴스 선정"
    )
    lines.append("- 비용: 무료")
    lines.append(f"- 원본 기사 수: {original_count}건")
    lines.append(f"- 유사 기사 제거 수: {removed_count}건")
    lines.append("")
    lines.append("---")
    lines.append("")

    append_recent_keywords(lines)

    today_articles = []

    for articles in grouped_articles.values():
        today_articles.extend(articles)

    rising_keywords = append_rising_keywords(lines, today_articles)
    append_hot_articles(lines, today_articles, rising_keywords)

    for section, articles in grouped_articles.items():
        append_section_report(lines, section, articles)

    return "\n".join(lines)


def generate_report(grouped_articles, date_str, original_count, removed_count):
    report_text = create_markdown_report(
        grouped_articles,
        date_str,
        original_count,
        removed_count,
    )

    output_path = save_report(report_text, date_str)

    return output_path