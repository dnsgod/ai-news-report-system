import re
from collections import Counter

from config import STOPWORDS


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


def extract_keywords(articles, top_n=8):
    counter = get_word_counter(articles)
    return counter.most_common(top_n)