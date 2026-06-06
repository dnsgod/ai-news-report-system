from services.sentiment_service import analyze_sentiment
from services.tag_service import assign_tags


def calculate_hot_score(article, rising_keywords):
    score = 0

    title = article.get("title", "")
    content = article.get("content", "")
    full_text = f"{title} {content}"

    if len(title) >= 20:
        score += 1

    for word, today_count, recent_count, rise_score in rising_keywords:
        if word in full_text:
            score += int(rise_score * 2)

    sentiment = analyze_sentiment(title, content)

    if sentiment == "부정":
        score += 3

    if len(content) >= 2000:
        score += 1

    return score


def get_hot_articles(articles, rising_keywords, top_n=5):
    scored_articles = []

    for article in articles:
        score = calculate_hot_score(article, rising_keywords)

        tags = assign_tags(
            article.get("title", ""),
            article.get("content", ""),
        )

        scored_articles.append(
            {
                "score": score,
                "title": article.get("title", ""),
                "press": article.get("press", ""),
                "link": article.get("link", ""),
                "tags": tags,
            }
        )

    scored_articles.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return scored_articles[:top_n]