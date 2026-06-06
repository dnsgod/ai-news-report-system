import requests

from config import MODEL_NAME, OLLAMA_URL


def call_ollama(prompt, timeout=120):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=timeout,
    )

    response.raise_for_status()

    result = response.json()
    return result.get("response", "").strip()


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

    try:
        return call_ollama(prompt, timeout=120)

    except Exception as e:
        print(f"[로컬 요약 실패] {title} / {e}")
        return "로컬 LLM 요약 생성에 실패했습니다."


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

    try:
        return call_ollama(prompt, timeout=180)

    except Exception as e:
        print(f"[섹션 요약 실패] {section_name} / {e}")
        return "섹션 요약 생성 실패"