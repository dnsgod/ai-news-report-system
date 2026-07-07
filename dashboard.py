import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.file_utils import get_today_str
from services.db_service import (
    search_articles,
    get_press_list,
    get_press_statistics,
    get_section_statistics,
    get_daily_statistics,
    get_tag_list,
)


def load_today_news_json():
    date_str = get_today_str()
    path = Path("data/raw") / f"naver_news_{date_str}.json"

    if not path.exists():
        return [], path

    with path.open("r", encoding="utf-8") as f:
        return json.load(f), path


def render_article_list(articles):
    for article in articles:
        title = article.get("title", "제목 없음")
        press = article.get("press", "언론사 미확인")
        section = article.get("section", "기타")
        link = article.get("link", "")
        content = article.get("content", "")
        crawled_at = article.get("crawled_at", "")
        sentiment = article.get("sentiment", "")
        tags = article.get("tags", "")

        with st.expander(f"[{section}] {title}"):
            st.write(f"**언론사:** {press}")

            if crawled_at:
                st.write(f"**수집 시각:** {crawled_at}")

            if sentiment:
                st.write(f"**분위기:** {sentiment}")
            else:
                st.write("**분위기:** 미분석")

            if tags:
                st.write(f"**태그:** {tags}")
            else:
                st.write("**태그:** 미분류")

            st.write(f"**링크:** {link}")

            if content:
                preview = content[:700].replace("\n", " ")
                st.write("**본문 미리보기**")
                st.write(preview + "...")
            else:
                st.write("본문이 없습니다.")


def main():
    st.set_page_config(
        page_title="AI 뉴스 리포트",
        page_icon="📰",
        layout="wide",
    )

    st.title("📰 AI 뉴스 리포트 대시보드")

    json_articles, path = load_today_news_json()

    if not json_articles:
        st.warning(f"오늘 뉴스 JSON 파일을 찾지 못했습니다: {path}")
        st.info("먼저 아래 명령어를 실행하세요.")
        st.code("python main.py")
        return

    df = pd.DataFrame(json_articles)

    st.caption(f"오늘 JSON 데이터 파일: {path}")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("오늘 수집 기사 수", len(df))

    with col2:
        st.metric("오늘 섹션 수", df["section"].nunique())

    st.divider()

    st.subheader("📊 누적 뉴스 통계")

    press_stats = get_press_statistics(limit=10)
    section_stats = get_section_statistics()
    daily_stats = get_daily_statistics(limit=14)

    col_press, col_section = st.columns(2)

    with col_press:
        st.write("**언론사별 기사 수 TOP 10**")

        if press_stats:
            press_df = pd.DataFrame(press_stats)
            st.bar_chart(press_df, x="press", y="count")
        else:
            st.info("언론사 통계 데이터가 없습니다.")

    with col_section:
        st.write("**섹션별 누적 기사 수**")

        if section_stats:
            section_df = pd.DataFrame(section_stats)
            st.bar_chart(section_df, x="section", y="count")
        else:
            st.info("섹션 통계 데이터가 없습니다.")

    st.write("**날짜별 수집 기사 수**")

    if daily_stats:
        daily_df = pd.DataFrame(daily_stats)
        st.line_chart(daily_df, x="date", y="count")
    else:
        st.info("날짜별 통계 데이터가 없습니다.")

    st.divider()

    st.subheader("🔎 뉴스 검색")

    keyword = st.text_input(
        "검색어 입력",
        placeholder="예: 반도체, AI, 환율, 삼성전자",
    )

    search_section = st.selectbox(
        "검색 섹션",
        ["전체", "정치", "경제", "사회", "생활문화", "세계", "IT과학"],
    )

    press_options = ["전체"] + get_press_list()

    search_press = st.selectbox(
        "언론사",
        press_options,
    )

    tag_options = ["전체"] + get_tag_list()

    search_tag = st.selectbox(
        "태그",
        tag_options,
    )

    search_sentiment = st.selectbox(
        "분위기",
        ["전체", "긍정", "중립", "부정"],
    )

    col_start, col_end = st.columns(2)

    with col_start:
        start_date = st.date_input("검색 시작일")

    with col_end:
        end_date = st.date_input("검색 종료일")

    search_limit = st.slider(
        "검색 결과 수",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
    )

    if st.button("검색"):
        if start_date > end_date:
            st.error("검색 시작일은 종료일보다 늦을 수 없습니다.")
        else:
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

            st.write(f"검색 결과: {len(results)}건")

            if not results:
                st.info("검색 결과가 없습니다.")
            else:
                render_article_list(results)

    st.divider()

    st.subheader("🗂 오늘 뉴스 보기")

    today = date.today()

    today_section = st.selectbox(
        "오늘 뉴스 섹션 선택",
        ["전체", "정치", "경제", "사회", "생활문화", "세계", "IT과학"],
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

    st.write(f"표시 기사 수: {len(today_articles)}건")

    if not today_articles:
        st.info(
            "오늘 날짜로 DB에 저장된 뉴스가 없습니다. "
            "python main.py를 실행해서 SQLite 저장까지 완료했는지 확인하세요."
        )
    else:
        render_article_list(today_articles)


if __name__ == "__main__":
    main()