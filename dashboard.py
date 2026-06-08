import json
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.file_utils import get_today_str


def load_today_news():
    date_str = get_today_str()
    path = Path("data/raw") / f"naver_news_{date_str}.json"

    if not path.exists():
        return [], path

    with path.open("r", encoding="utf-8") as f:
        return json.load(f), path


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
    st.metric("수집 기사 수", len(df))

    st.divider()

    st.subheader("📌 섹션별 기사 수")

    section_counts = df["section"].value_counts()

    st.bar_chart(section_counts)

    st.divider()

    st.subheader("🗂 섹션별 뉴스 보기")

    sections = ["전체"] + sorted(df["section"].dropna().unique().tolist())
    selected_section = st.selectbox("섹션 선택", sections)

    if selected_section != "전체":
        filtered_df = df[df["section"] == selected_section]
    else:
        filtered_df = df

    st.write(f"표시 기사 수: {len(filtered_df)}건")

    for _, row in filtered_df.iterrows():
        title = row.get("title", "제목 없음")
        press = row.get("press", "언론사 미확인")
        link = row.get("link", "")
        content = row.get("content", "")

        with st.expander(title):
            st.write(f"**언론사:** {press}")
            st.write(f"**링크:** {link}")

            if content:
                preview = content[:500].replace("\n", " ")
                st.write("**본문 미리보기**")
                st.write(preview + "...")
            else:
                st.write("본문이 수집되지 않았습니다.")


if __name__ == "__main__":
    main()