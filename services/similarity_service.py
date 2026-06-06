from difflib import SequenceMatcher


def title_similarity(title1, title2):
    return SequenceMatcher(None, title1, title2).ratio()


def remove_similar_articles(articles, threshold=0.72):
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