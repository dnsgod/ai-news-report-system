import json
import re
import time
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"


STOPWORDS = {
    "그리고", "하지만", "또한", "대한", "관련", "이번", "지난", "오늘",
    "기자", "뉴스", "사진", "보도", "영상", "때문", "위해", "통해",
    "있는", "없는", "했다", "한다", "된다", "등은", "등이", "등을",
    "에서", "으로", "에게", "까지", "부터", "보다", "라고", "하고",
    "습니다", "입니다", "관련해", "것으로", "것이다", "것은", "것을",
}


def get_today_str():
    return datetime.now().strftime("%Y%m%d")


def load_news_json(date_str):
    input_path = Path("data/raw") / f"naver_news_{date_str}.json"

    if not input_path.exists():
        raise FileNotFoundError(f"뉴스 파일을 찾을 수 없습니다: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def title_similarity(title1, title2):
    return SequenceMatcher(None, title1, title2).ratio()


def remove_similar_articles(articles, threshold=0.72):
    """
    제목이 비슷한 기사를 중복으로 보고 제거한다.
    threshold가 낮을수록 더 많이 제거된다.
    """
    unique_articles = []
    removed_count = 0

    for article in articles:
        title = article.get("title", "")

        is_duplicate = False

        for saved_article in unique_articles:
            saved_title = saved_article.get("title", "")
            similarity = title_similarity(title, saved_title)

            if similarity >= threshold:
                is_duplicate = True
                removed_count += 1
                break

        if not is_duplicate:
            unique_articles.append(article)

    return unique_articles, removed_count


def local_llm_summary(title, content):
    if not content:
        return "본문이 수집되지 않아 요약할 수 없습니다."

    content = content.replace("\n", " ").strip()
    content = content[:2500]

    prompt = f"""
다음 뉴스 기사를 한국어로 3줄 이내로 요약해줘.

조건:
- 핵심 사건을 먼저 말해줘
- 원인이나 배경이 있으면 포함해줘
- 의미나 영향이 있으면 포함해줘
- 기사에 없는 내용은 추측하지 마
- 문장은 짧고 명확하게 써줘

제목:
{title}

본문:
{content}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()

        result = response.json()
        return result.get("response", "").strip()

    except Exception as e:
        print(f"[로컬 요약 실패] {title} / {e}")
        return "로컬 LLM 요약 생성에 실패했습니다."


def extract_keywords(articles, top_n=8):
    text = ""

    for article in articles:
        title = article.get("title", "")
        content = article.get("content", "")
        text += " " + title + " " + content

    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)

    cleaned_words = []

    for word in words:
        word = word.strip()

        if word in STOPWORDS:
            continue

        cleaned_words.append(word)

    counter = Counter(cleaned_words)

    return counter.most_common(top_n)


def summarize_section(section_name, articles):
    combined_text = ""

    for article in articles:
        title = article.get("title", "")
        content = article.get("content", "")

        combined_text += f"\n제목: {title}\n"
        combined_text += f"내용: {content[:1000]}\n"

    combined_text = combined_text[:6000]

    prompt = f"""
다음은 {section_name} 뉴스 기사들이다.

이 뉴스들의 전체적인 흐름과 핵심 이슈를
한국어로 3줄 정도로 요약해줘.

조건:
- 전체 분위기 중심
- 반복 설명 금지
- 핵심 이슈 위주
- 짧고 명확하게
- 기사에 없는 내용은 추측하지 마

뉴스 데이터:
{combined_text}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()

        result = response.json()
        return result.get("response", "").strip()

    except Exception as e:
        print(f"[섹션 요약 실패] {section_name} / {e}")
        return "섹션 요약 생성 실패"

def load_recent_news_files(days=3, exclude_today=False):
    raw_dir = Path("data/raw")

    if not raw_dir.exists():
        return []

    files = sorted(
        raw_dir.glob("naver_news_*.json"),
        reverse=True
    )

    recent_files = files[:days]

    all_articles = []

    today_str = get_today_str()

    for file_path in recent_files:

        if exclude_today and today_str in file_path.name:
            continue

        try:
            with file_path.open("r", encoding="utf-8") as f:
                articles = json.load(f)
                all_articles.extend(articles)

        except Exception as e:
            print(f"[최근 파일 읽기 실패] {file_path} / {e}")

    return all_articles

def get_recent_keywords(days=3, top_n=10):
    """
    최근 며칠간 저장된 뉴스 파일을 읽고 반복 키워드를 추출한다.
    """
    recent_articles = load_recent_news_files(days=days)

    if not recent_articles:
        return []

    return extract_keywords(recent_articles, top_n=top_n)

def get_word_counter(articles):
    text = ""

    for article in articles:
        title = article.get("title", "")
        content = article.get("content", "")
        text += " " + title + " " + content

    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)

    cleaned_words = []

    for word in words:
        word = word.strip()

        if word in STOPWORDS:
            continue

        cleaned_words.append(word)

    return Counter(cleaned_words)

def get_rising_keywords(today_articles, days=3, top_n=10):
    """
    오늘 기사와 최근 기사들을 비교해서 급상승 키워드를 찾는다.
    """
    today_counter = get_word_counter(today_articles)
    recent_articles = load_recent_news_files(
        days=days,
        exclude_today=True
    )

    if not recent_articles:
        return []

    recent_counter = get_word_counter(recent_articles)

    rising = []

    for word, today_count in today_counter.items():
        if today_count < 2:
            continue

        recent_count = recent_counter.get(word, 0)

        # 최근에도 많던 단어는 급상승으로 보기 어렵다
        score = today_count / (recent_count + 1)

        if score >= 1.5:
            rising.append((word, today_count, recent_count, score))

    rising.sort(key=lambda x: x[3], reverse=True)

    return rising[:top_n]

def group_by_section(articles):
    grouped = {}

    for article in articles:
        section = article.get("section", "기타")

        if section not in grouped:
            grouped[section] = []

        grouped[section].append(article)

    return grouped


def create_markdown_report(grouped_articles, date_str, original_count, removed_count):
    lines = []

    lines.append("# 📰 네이버 뉴스 아침 리포트")
    lines.append("")
    lines.append(f"- 생성 날짜: {date_str}")
    lines.append("- 기준: 네이버 뉴스 섹션별 헤드라인")
    lines.append("- 요약 방식: Ollama 로컬 LLM")
    lines.append("- 분석 기능: 키워드 추출, 섹션 요약, 유사 기사 제거")
    lines.append("- 비용: 무료")
    lines.append(f"- 원본 기사 수: {original_count}건")
    lines.append(f"- 유사 기사 제거 수: {removed_count}건")
    lines.append("")
    lines.append("---")
    lines.append("")

    recent_keywords = get_recent_keywords(days=3, top_n=10)

    lines.append("## 🔁 최근 3일 반복 키워드")
    lines.append("")

    if recent_keywords:
        keyword_text = ", ".join([word for word, count in recent_keywords])
        lines.append(keyword_text)
    else:
        lines.append("최근 키워드를 추출하지 못했습니다.")

    today_articles = []

    for articles in grouped_articles.values():
        today_articles.extend(articles)

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

    lines.append("")
    lines.append("---")
    lines.append("")

    for section, articles in grouped_articles.items():
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

        for idx, article in enumerate(articles, start=1):
            title = article.get("title", "제목 없음")
            press = article.get("press") or "언론사 미확인"
            link = article.get("link", "")
            content = article.get("content", "")

            print(f"[요약 중] {section} - {title[:40]}...")

            summary = local_llm_summary(title, content)

            lines.append(f"### {idx}. {title}")
            lines.append("")
            lines.append(f"- 언론사: {press}")
            lines.append(f"- 링크: {link}")
            lines.append("")
            lines.append("**AI 요약**")
            lines.append("")
            lines.append(summary)
            lines.append("")
            lines.append("---")
            lines.append("")

            time.sleep(0.3)

    return "\n".join(lines)


def save_report(report_text, date_str):
    output_dir = Path("reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"daily_news_report_{date_str}.md"

    with output_path.open("w", encoding="utf-8") as f:
        f.write(report_text)

    return output_path


def main():
    date_str = get_today_str()

    articles = load_news_json(date_str)
    original_count = len(articles)

    unique_articles, removed_count = remove_similar_articles(
        articles,
        threshold=0.72,
    )

    grouped_articles = group_by_section(unique_articles)

    report_text = create_markdown_report(
        grouped_articles,
        date_str,
        original_count,
        removed_count,
    )

    output_path = save_report(report_text, date_str)

    print(f"\n리포트 생성 완료: {output_path}")
    print(f"원본 기사 수: {original_count}건")
    print(f"유사 기사 제거 수: {removed_count}건")
    print(f"최종 기사 수: {len(unique_articles)}건")
    print(f"섹션 수: {len(grouped_articles)}개")


if __name__ == "__main__":
    main()