import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SECTIONS = {
    "politics": {"name": "정치", "code": "100"},
    "economy": {"name": "경제", "code": "101"},
    "society": {"name": "사회", "code": "102"},
    "life": {"name": "생활문화", "code": "103"},
    "world": {"name": "세계", "code": "104"},
    "it": {"name": "IT과학", "code": "105"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_html(url):
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return response.text


def fetch_article_body(article_url):
    try:
        html = fetch_html(article_url)
        soup = BeautifulSoup(html, "html.parser")

        body_tag = soup.select_one("#dic_area")

        if not body_tag:
            body_tag = soup.select_one("#articeBody")

        if not body_tag:
            return ""

        for tag in body_tag.select("script, style, span.end_photo_org, em.img_desc"):
            tag.decompose()

        return body_tag.get_text(separator="\n", strip=True)

    except Exception as e:
        print(f"  [본문 수집 실패] {article_url} / {e}")
        return ""


def parse_headlines(html, section_name, limit=5):
    soup = BeautifulSoup(html, "html.parser")

    articles = []
    seen_links = set()

    title_links = soup.select("a.sa_text_title")

    for tag in title_links:
        title = tag.get_text(strip=True)
        link = tag.get("href")

        if not title or not link:
            continue

        link = urljoin("https://news.naver.com", link)

        if link in seen_links:
            continue

        seen_links.add(link)

        article_box = tag.find_parent("li")
        press = ""

        if article_box:
            press_tag = article_box.select_one(".sa_text_press")
            if press_tag:
                press = press_tag.get_text(strip=True)

        print(f"  - 본문 수집 중: {title[:40]}...")

        content = fetch_article_body(link)
        time.sleep(0.5)

        articles.append(
            {
                "section": section_name,
                "title": title,
                "link": link,
                "press": press,
                "content": content,
                "content_length": len(content),
                "crawled_at": datetime.now().isoformat(timespec="seconds"),
            }
        )

        if len(articles) >= limit:
            break

    return articles


def crawl_section(section_info, limit=5):
    section_name = section_info["name"]
    section_code = section_info["code"]
    url = f"https://news.naver.com/section/{section_code}"

    print(f"\n[{section_name}] 크롤링 시작")
    print(url)

    html = fetch_html(url)
    articles = parse_headlines(html, section_name, limit=limit)

    print(f"[{section_name}] 수집 완료: {len(articles)}건")
    return articles


def save_json(data):
    today = datetime.now().strftime("%Y%m%d")

    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"naver_news_{today}.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return output_path


def print_result(articles):
    current_section = None

    for article in articles:
        if current_section != article["section"]:
            current_section = article["section"]
            print(f"\n=== {current_section} ===")

        press = article["press"] or "언론사 미확인"
        content_preview = article["content"][:80].replace("\n", " ")

        print(f"- [{press}] {article['title']}")
        print(f"  본문 길이: {article['content_length']}자")
        print(f"  미리보기: {content_preview}...")
        print(f"  링크: {article['link']}")


def main():
    all_articles = []

    for section_key, section_info in SECTIONS.items():
        try:
            articles = crawl_section(section_info, limit=5)
            all_articles.extend(articles)
            time.sleep(1)

        except Exception as e:
            print(f"[ERROR] {section_info['name']} 크롤링 실패: {e}")

    print_result(all_articles)

    output_path = save_json(all_articles)
    print(f"\n저장 완료: {output_path}")
    print(f"총 수집 기사 수: {len(all_articles)}건")


if __name__ == "__main__":
    main()