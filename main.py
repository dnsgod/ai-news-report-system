from crawler import main as crawl_main
from report_generator import generate_report
from services.similarity_service import remove_similar_articles
from utils.file_utils import get_today_str, load_news_json


def group_by_section(articles):
    grouped = {}

    for article in articles:
        section = article.get("section", "기타")

        if section not in grouped:
            grouped[section] = []

        grouped[section].append(article)

    return grouped


def main():
    print("[1/3] 뉴스 크롤링 시작")
    crawl_main()

    print("[2/3] 수집 데이터 로드")
    date_str = get_today_str()
    articles = load_news_json(date_str)

    original_count = len(articles)

    unique_articles, removed_count = remove_similar_articles(
        articles,
        threshold=0.72,
    )

    grouped_articles = group_by_section(unique_articles)

    print("[3/3] 리포트 생성 시작")
    output_path = generate_report(
        grouped_articles=grouped_articles,
        date_str=date_str,
        original_count=original_count,
        removed_count=removed_count,
    )

    print("\n전체 파이프라인 완료")
    print(f"리포트 위치: {output_path}")
    print(f"원본 기사 수: {original_count}건")
    print(f"유사 기사 제거 수: {removed_count}건")
    print(f"최종 기사 수: {len(unique_articles)}건")
    print(f"섹션 수: {len(grouped_articles)}개")


if __name__ == "__main__":
    main()