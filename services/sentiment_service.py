import time

from services.llm_service import call_ollama


def analyze_sentiment(title, content):
    if not content:
        return "중립"

    content = content.replace("\n", " ").strip()
    content = content[:1500]

    prompt = f"""
다음 뉴스 기사의 분위기를 분류해줘.

반드시 아래 셋 중 하나만 답해.
긍정
중립
부정

판단 기준:
- 긍정: 성장, 성과, 개선, 회복, 협력, 성공
- 중립: 단순 사실 전달, 일정, 발표, 설명
- 부정: 사고, 갈등, 하락, 위기, 범죄, 불확실성, 피해

제목:
{title}

본문:
{content}
"""

    try:
        answer = call_ollama(prompt, timeout=120)

        if "긍정" in answer:
            return "긍정"
        elif "부정" in answer:
            return "부정"
        else:
            return "중립"

    except Exception as e:
        print(f"[감정 분석 실패] {title} / {e}")
        return "중립"


def analyze_section_sentiment(articles):
    result = {
        "긍정": 0,
        "중립": 0,
        "부정": 0,
    }

    for article in articles:
        title = article.get("title", "")
        content = article.get("content", "")

        print(f"[감정 분석 중] {title[:40]}...")

        sentiment = analyze_sentiment(title, content)

        if sentiment not in result:
            sentiment = "중립"

        result[sentiment] += 1
        time.sleep(0.2)

    return result