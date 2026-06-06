from services.keyword_service import extract_keywords, get_word_counter
from utils.file_utils import load_recent_news_files


def get_recent_keywords(days=3, top_n=10):
    recent_articles = load_recent_news_files(days=days)

    if not recent_articles:
        return []

    return extract_keywords(recent_articles, top_n=top_n)


def get_rising_keywords(today_articles, days=3, top_n=10):
    today_counter = get_word_counter(today_articles)

    recent_articles = load_recent_news_files(
        days=days,
        exclude_today=True,
    )

    if not recent_articles:
        return []

    recent_counter = get_word_counter(recent_articles)

    rising = []

    for word, today_count in today_counter.items():
        if today_count < 2:
            continue

        recent_count = recent_counter.get(word, 0)
        score = today_count / (recent_count + 1)

        if score >= 1.5:
            rising.append((word, today_count, recent_count, score))

    rising.sort(key=lambda x: x[3], reverse=True)

    return rising[:top_n]