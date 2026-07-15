import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from services.db_service import (
    get_daily_statistics,
    get_press_list,
    get_press_statistics,
    get_section_statistics,
    get_sentiment_statistics,
    get_tag_list,
    get_tag_statistics,
    search_articles,
)
from services.rag_service import answer_news_question
from utils.file_utils import get_today_str


SECTION_OPTIONS = [
    "전체",
    "정치",
    "경제",
    "사회",
    "생활문화",
    "세계",
    "IT과학",
]

SENTIMENT_OPTIONS = [
    "전체",
    "긍정",
    "중립",
    "부정",
]


def load_today_news_json():
    """
    오늘 날짜의 원본 뉴스 JSON 파일을 읽는다.
    """

    date_str = get_today_str()

    path = (
        Path("data/raw")
        / f"naver_news_{date_str}.json"
    )

    if not path.exists():
        return [], path

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        articles = json.load(file)

    return articles, path


def render_article_list(
    articles,
    show_hybrid_score=False,
):
    """
    기사 목록을 Streamlit expander 형태로 출력한다.
    """

    for article in articles:
        title = (
            article.get("title")
            or "제목 없음"
        )

        press = (
            article.get("press")
            or "언론사 미확인"
        )

        section = (
            article.get("section")
            or "기타"
        )

        link = article.get("link") or ""
        content = article.get("content") or ""
        crawled_at = article.get("crawled_at") or ""
        sentiment = article.get("sentiment") or ""
        tags = article.get("tags") or ""

        hybrid_score = article.get(
            "hybrid_score",
            0.0,
        )

        keyword_score = article.get(
            "normalized_keyword_score",
            0.0,
        )

        vector_score = article.get(
            "normalized_vector_score",
            0.0,
        )

        retrieval_source = article.get(
            "retrieval_source",
            "",
        )

        with st.expander(
            f"[{section}] {title}"
        ):
            st.write(
                f"**언론사:** {press}"
            )

            if crawled_at:
                st.write(
                    f"**수집 시각:** {crawled_at}"
                )

            if sentiment:
                st.write(
                    f"**분위기:** {sentiment}"
                )
            else:
                st.write(
                    "**분위기:** 미분석"
                )

            if tags:
                st.write(
                    f"**태그:** {tags}"
                )
            else:
                st.write(
                    "**태그:** 미분류"
                )

            if show_hybrid_score:
                st.write(
                    f"**검색 방식:** "
                    f"{retrieval_source}"
                )

                st.write(
                    f"**하이브리드 점수:** "
                    f"{hybrid_score:.4f}"
                )

                st.write(
                    f"**키워드 점수:** "
                    f"{keyword_score:.4f}"
                )

                st.write(
                    f"**벡터 유사도:** "
                    f"{vector_score:.4f}"
                )

            if link:
                st.link_button(
                    "원문 기사 열기",
                    link,
                )

            if content:
                preview = (
                    content[:700]
                    .replace("\n", " ")
                )

                st.write(
                    "**본문 미리보기**"
                )

                st.write(
                    preview + "..."
                )
            else:
                st.write(
                    "본문이 없습니다."
                )


def render_sentiment_statistics():
    """
    SQLite의 감정 분석 결과를 집계하여 표시한다.
    """

    st.write(
        "### 😊 뉴스 감정 분석 현황"
    )

    sentiment_stats = (
        get_sentiment_statistics()
    )

    if not sentiment_stats:
        st.info(
            "감정 분석 통계 데이터가 없습니다."
        )
        return

    sentiment_map = {
        item["sentiment"]: item
        for item in sentiment_stats
    }

    positive = sentiment_map.get(
        "긍정",
        {
            "count": 0,
            "percentage": 0.0,
        },
    )

    neutral = sentiment_map.get(
        "중립",
        {
            "count": 0,
            "percentage": 0.0,
        },
    )

    negative = sentiment_map.get(
        "부정",
        {
            "count": 0,
            "percentage": 0.0,
        },
    )

    total_count = (
        positive["count"]
        + neutral["count"]
        + negative["count"]
    )

    (
        col_total,
        col_positive,
        col_neutral,
        col_negative,
    ) = st.columns(4)

    with col_total:
        st.metric(
            "분석 기사",
            f"{total_count}건",
        )

    with col_positive:
        st.metric(
            "긍정",
            f"{positive['count']}건",
            f"{positive['percentage']:.1f}%",
        )

    with col_neutral:
        st.metric(
            "중립",
            f"{neutral['count']}건",
            f"{neutral['percentage']:.1f}%",
        )

    with col_negative:
        st.metric(
            "부정",
            f"{negative['count']}건",
            f"{negative['percentage']:.1f}%",
        )

    sentiment_df = pd.DataFrame(
        sentiment_stats
    )

    st.bar_chart(
        sentiment_df,
        x="sentiment",
        y="count",
    )

    if total_count > 0:
        dominant_sentiment = max(
            sentiment_stats,
            key=lambda item: item["count"],
        )

        st.caption(
            f"가장 많은 감정 유형은 "
            f"'{dominant_sentiment['sentiment']}'이며, "
            f"전체 분석 기사의 "
            f"{dominant_sentiment['percentage']:.1f}%입니다."
        )
    else:
        st.info(
            "아직 감정 분석이 완료된 기사가 없습니다."
        )


def render_tag_statistics():
    """
    SQLite에 저장된 태그를 집계하여 TOP10을 표시한다.
    """

    st.write(
        "### 🏷️ 주요 뉴스 태그 TOP 10"
    )

    tag_stats = get_tag_statistics(
        limit=10,
    )

    if not tag_stats:
        st.info(
            "태그 통계 데이터가 없습니다."
        )
        return

    top_tag = tag_stats[0]

    total_top10_count = sum(
        item["count"]
        for item in tag_stats
    )

    col_top_tag, col_tag_count = (
        st.columns(2)
    )

    with col_top_tag:
        st.metric(
            "가장 많이 등장한 태그",
            top_tag["tag"],
            f"{top_tag['count']}회",
        )

    with col_tag_count:
        st.metric(
            "TOP10 태그 등장 횟수",
            f"{total_top10_count}회",
        )

    tag_df = pd.DataFrame(
        tag_stats
    )

    st.bar_chart(
        tag_df,
        x="tag",
        y="count",
    )

    st.write(
        "**태그별 상세 통계**"
    )

    display_df = tag_df.copy()

    display_df["percentage"] = (
        display_df["percentage"]
        .map(lambda value: f"{value:.1f}%")
    )

    display_df = display_df.rename(
        columns={
            "tag": "태그",
            "count": "등장 횟수",
            "percentage": "전체 태그 비율",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"현재 가장 많이 등장한 태그는 "
        f"'{top_tag['tag']}'이며 "
        f"총 {top_tag['count']}회 등장했습니다."
    )


def render_basic_statistics():
    """
    언론사, 섹션, 날짜별 통계를 출력한다.
    """

    press_stats = get_press_statistics(
        limit=10,
    )

    section_stats = (
        get_section_statistics()
    )

    daily_stats = get_daily_statistics(
        limit=14,
    )

    col_press, col_section = (
        st.columns(2)
    )

    with col_press:
        st.write(
            "**언론사별 기사 수 TOP 10**"
        )

        if press_stats:
            press_df = pd.DataFrame(
                press_stats
            )

            st.bar_chart(
                press_df,
                x="press",
                y="count",
            )
        else:
            st.info(
                "언론사 통계 데이터가 없습니다."
            )

    with col_section:
        st.write(
            "**섹션별 누적 기사 수**"
        )

        if section_stats:
            section_df = pd.DataFrame(
                section_stats
            )

            st.bar_chart(
                section_df,
                x="section",
                y="count",
            )
        else:
            st.info(
                "섹션 통계 데이터가 없습니다."
            )

    st.write(
        "**날짜별 수집 기사 수**"
    )

    if daily_stats:
        daily_df = pd.DataFrame(
            daily_stats
        )

        st.line_chart(
            daily_df,
            x="date",
            y="count",
        )
    else:
        st.info(
            "날짜별 통계 데이터가 없습니다."
        )


def render_statistics():
    """
    누적 뉴스 통계 화면 전체를 출력한다.
    """

    st.subheader(
        "📊 누적 뉴스 통계"
    )

    render_basic_statistics()

    st.divider()

    col_sentiment, col_tag = (
        st.columns(2)
    )

    with col_sentiment:
        render_sentiment_statistics()

    with col_tag:
        render_tag_statistics()


def render_ai_assistant():
    """
    하이브리드 검색 기반 AI 뉴스 비서 화면이다.
    """

    st.subheader(
        "🤖 AI 뉴스 비서"
    )

    st.caption(
        "질문에서 키워드를 추출하고, "
        "SQLite 키워드 검색과 벡터 검색을 "
        "결합해 관련 기사를 찾습니다."
    )

    question = st.text_input(
        "뉴스에 대해 질문해보세요",
        placeholder=(
            "예: 인공지능 산업 투자와 "
            "관련된 소식을 정리해줘"
        ),
        key="rag_question",
    )

    rag_limit = st.slider(
        "AI가 참고할 기사 수",
        min_value=3,
        max_value=10,
        value=5,
        step=1,
        key="rag_limit",
    )

    if st.button(
        "AI에게 질문하기",
        key="rag_button",
    ):
        if not question.strip():
            st.warning(
                "질문을 입력해주세요."
            )
            return

        with st.spinner(
            "키워드 검색과 벡터 검색을 "
            "결합해 관련 뉴스를 찾는 중입니다..."
        ):
            result = answer_news_question(
                question=question,
                limit=rag_limit,
            )

        keywords = result.get(
            "keywords",
            [],
        )

        search_type = result.get(
            "search_type",
            "",
        )

        if keywords:
            st.write(
                "**추출된 검색 키워드**"
            )

            st.write(
                " · ".join(keywords)
            )

        if search_type:
            st.write(
                f"**검색 방식:** {search_type}"
            )

        st.write(
            "### AI 답변"
        )

        st.write(
            result["answer"]
        )

        if result["articles"]:
            st.write(
                "### 참고 기사"
            )

            render_article_list(
                result["articles"],
                show_hybrid_score=True,
            )


def render_news_search():
    """
    뉴스 조건 검색 화면이다.
    """

    st.subheader(
        "🔎 뉴스 검색"
    )

    keyword = st.text_input(
        "검색어 입력",
        placeholder=(
            "예: 반도체, AI, 환율, 삼성전자"
        ),
        key="search_keyword",
    )

    search_section = st.selectbox(
        "검색 섹션",
        SECTION_OPTIONS,
        key="search_section",
    )

    press_options = (
        ["전체"]
        + get_press_list()
    )

    search_press = st.selectbox(
        "언론사",
        press_options,
        key="search_press",
    )

    tag_options = (
        ["전체"]
        + get_tag_list()
    )

    search_tag = st.selectbox(
        "태그",
        tag_options,
        key="search_tag",
    )

    search_sentiment = st.selectbox(
        "분위기",
        SENTIMENT_OPTIONS,
        key="search_sentiment",
    )

    col_start, col_end = (
        st.columns(2)
    )

    with col_start:
        start_date = st.date_input(
            "검색 시작일",
            key="search_start_date",
        )

    with col_end:
        end_date = st.date_input(
            "검색 종료일",
            key="search_end_date",
        )

    search_limit = st.slider(
        "검색 결과 수",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
        key="search_limit",
    )

    if st.button(
        "검색",
        key="search_button",
    ):
        if start_date > end_date:
            st.error(
                "검색 시작일은 종료일보다 "
                "늦을 수 없습니다."
            )
            return

        results = search_articles(
            keyword=keyword,
            section=search_section,
            press=search_press,
            tag=search_tag,
            sentiment=search_sentiment,
            start_date=start_date,
            end_date=end_date,
            limit=search_limit,
        )

        st.write(
            f"검색 결과: "
            f"{len(results)}건"
        )

        if not results:
            st.info(
                "검색 결과가 없습니다."
            )
        else:
            render_article_list(
                results
            )


def render_today_news():
    """
    오늘 SQLite에 저장된 뉴스를 출력한다.
    """

    st.subheader(
        "🗂 오늘 뉴스 보기"
    )

    today = date.today()

    today_section = st.selectbox(
        "오늘 뉴스 섹션 선택",
        SECTION_OPTIONS,
        key="today_section",
    )

    today_articles = search_articles(
        keyword="",
        section=today_section,
        press="전체",
        tag="전체",
        sentiment="전체",
        start_date=today,
        end_date=today,
        limit=100,
    )

    st.write(
        f"표시 기사 수: "
        f"{len(today_articles)}건"
    )

    if not today_articles:
        st.info(
            "오늘 날짜로 DB에 저장된 "
            "뉴스가 없습니다. "
            "python main.py를 실행해 주세요."
        )
    else:
        render_article_list(
            today_articles
        )


def render_header_metrics(
    json_articles,
    path,
):
    """
    상단 기본 정보와 오늘 수집 현황을 출력한다.
    """

    df = pd.DataFrame(
        json_articles
    )

    st.caption(
        f"오늘 JSON 데이터 파일: {path}"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "오늘 수집 기사 수",
            len(df),
        )

    with col2:
        section_count = (
            df["section"].nunique()
            if "section" in df.columns
            else 0
        )

        st.metric(
            "오늘 섹션 수",
            section_count,
        )


def main():
    st.set_page_config(
        page_title="AI 뉴스 리포트",
        page_icon="📰",
        layout="wide",
    )

    st.title(
        "📰 AI 뉴스 리포트 대시보드"
    )

    json_articles, path = (
        load_today_news_json()
    )

    if not json_articles:
        st.warning(
            f"오늘 뉴스 JSON 파일을 "
            f"찾지 못했습니다: {path}"
        )

        st.info(
            "먼저 아래 명령어를 실행하세요."
        )

        st.code(
            "python main.py"
        )

        return

    render_header_metrics(
        json_articles=json_articles,
        path=path,
    )

    st.divider()
    render_statistics()

    st.divider()
    render_ai_assistant()

    st.divider()
    render_news_search()

    st.divider()
    render_today_news()


if __name__ == "__main__":
    main()