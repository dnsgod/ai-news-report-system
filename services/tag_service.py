from config import TAG_RULES


def assign_tags(title, content, max_tags=3):
    text = f"{title} {content}"

    matched_tags = []

    for tag, keywords in TAG_RULES.items():
        for keyword in keywords:
            if keyword in text:
                matched_tags.append(tag)
                break

    if not matched_tags:
        return ["기타"]

    return matched_tags[:max_tags]