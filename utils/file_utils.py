import json
from datetime import datetime
from pathlib import Path

from config import RAW_DATA_DIR, REPORT_DIR


def get_today_str():
    return datetime.now().strftime("%Y%m%d")


def load_news_json(date_str):
    input_path = Path(RAW_DATA_DIR) / f"naver_news_{date_str}.json"

    if not input_path.exists():
        raise FileNotFoundError(f"뉴스 파일을 찾을 수 없습니다: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_report(report_text, date_str):
    output_dir = Path(REPORT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"daily_news_report_{date_str}.md"

    with output_path.open("w", encoding="utf-8") as f:
        f.write(report_text)

    return output_path


def load_recent_news_files(days=3, exclude_today=False):
    raw_dir = Path(RAW_DATA_DIR)

    if not raw_dir.exists():
        return []

    files = sorted(
        raw_dir.glob("naver_news_*.json"),
        reverse=True,
    )

    all_articles = []
    today_str = get_today_str()
    loaded_count = 0

    for file_path in files:
        if exclude_today and today_str in file_path.name:
            continue

        if loaded_count >= days:
            break

        try:
            with file_path.open("r", encoding="utf-8") as f:
                articles = json.load(f)
                all_articles.extend(articles)
                loaded_count += 1

        except Exception as e:
            print(f"[최근 파일 읽기 실패] {file_path} / {e}")

    return all_articles