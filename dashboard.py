import json
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
)


def load_today_news():
    """
    오늘 날짜의 JSON 뉴스 파일을 읽어온다.
    파일 위치:
    data/raw/naver_news_YYYYMMDD.json
    """

    date_str = get_today_str()
    path = Path("data/raw") / f"naver_news_{date_str}.json"

    if not path.exists():
        return [], path

    with path.open("r", encoding="utf-8") as f:
        return json.load(f), path


def render_article_list(articles):
    """
    기사 목록을 Streamlit 화면에 출력한다.
    """

    for article in articles:
        title = article.get("title", "제목 없음")
        press = article.get("press", "언론사 미확인")
        section = article.get("section", "기타")
        link = article.get("link", "")
        content = article.get("content", "")
        crawled_at = article.get("crawled_at", "")

        with st.expander(f"[{section}] {title}"):
            st.write(f"**언론사:** {press}")

            if crawled_at:
                st.write(f"**수집 시각:** {crawled_at}")

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

    articles, path = load_today_news()

    if not articles:
        st.warning(f"오늘 뉴스 파일을 찾지 못했습니다: {path}")
        st.info("먼저 아래 명령어를 실행하세요.")
        st.code("python main.py")
        return

    df = pd.DataFrame(articles)

    st.caption(f"데이터 파일: {path}")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("수집 기사 수", len(df))

    with col2:
        st.metric("섹션 수", df["section"].nunique())

    st.divider()

    st.subheader("📊 누적 뉴스 통계")

    keyword = st.text_input(
        "검색어 입력",
        placeholder="예: 반도체, AI, 환율, 삼성전자",
    )
    press_stats = get_press_statistics(limit=10)
    section_stats = get_section_statistics()
    daily_stats = get_daily_statistics(limit=14)

    col_press, col_section = st.columns(2)

    with col_press:
        st.write("**언론사별 기사 수 TOP 10**")

        if press_stats:
            press_df = pd.DataFrame(press_stats)
            st.bar_chart(
                press_df,
                x="press",
                y="count",
            )
        else:
            st.info("언론사 통계 데이터가 없습니다.")

    with col_section:
        st.write("**섹션별 누적 기사 수**")

        if section_stats:
            section_df = pd.DataFrame(section_stats)
            st.bar_chart(
                section_df,
                x="section",
                y="count",
            )
        else:
            st.info("섹션 통계 데이터가 없습니다.")

    st.write("**날짜별 수집 기사 수**")

    if daily_stats:
        daily_df = pd.DataFrame(daily_stats)
        st.line_chart(
            daily_df,
            x="date",
            y="count",
        )
    else:
        st.info("날짜별 통계 데이터가 없습니다.")

    search_section = st.selectbox(
        "검색 섹션",
        ["전체", "정치", "경제", "사회", "생활문화", "세계", "IT과학"],
    )

    press_options = ["전체"] + get_press_list()

    search_press = st.selectbox(
        "언론사",
        press_options,
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

    sections = ["전체"] + sorted(df["section"].dropna().unique().tolist())

    selected_section = st.selectbox(
        "오늘 뉴스 섹션 선택",
        sections,
    )

    if selected_section != "전체":
        filtered_df = df[df["section"] == selected_section]
    else:
        filtered_df = df

    st.write(f"표시 기사 수: {len(filtered_df)}건")

    today_articles = filtered_df.to_dict(orient="records")
    render_article_list(today_articles)


if __name__ == "__main__":
    main()