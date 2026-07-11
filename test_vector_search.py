from services.vector_service import (
    search_similar_articles,
)


def main():
    query = input(
        "검색할 뉴스 질문: "
    ).strip()

    results = search_similar_articles(
        query=query,
        top_n=5,
    )

    if not results:
        print(
            "관련 기사를 찾지 못했습니다."
        )
        return

    print()
    print("벡터 검색 결과")
    print("=" * 60)

    for index, article in enumerate(
        results,
        start=1,
    ):
        print(
            f"{index}. {article['title']}"
        )
        print(
            f"   섹션: {article['section']}"
        )
        print(
            f"   언론사: {article['press']}"
        )
        print(
            f"   유사도: "
            f"{article['vector_score']:.4f}"
        )
        print(
            f"   링크: {article['link']}"
        )
        print()


if __name__ == "__main__":
    main()