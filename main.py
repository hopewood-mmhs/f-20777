import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="영화 데이터 그래프 도감 1 - 시간",
    page_icon="🎬",
    layout="wide",
)


# 데이터 로드 및 전처리 함수
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"
    df = pd.read_csv(url)

    # 열 이름 설정 (데이터 형태에 맞게 매핑)
    df.columns = [
        "날짜",
        "순위",
        "영화코드",
        "영화명",
        "일관객",
        "누적관객",
        "스크린수",
        "상영횟수",
    ]

    # 날짜 열을 datetime 타입으로 변환 (YYYYMMDD 형식)
    df["날짜"] = pd.to_datetime(df["날짜"].astype(str), format="%Y%m%d")

    return df


# 앱 타이틀
st.title("🎬 영화 데이터 그래프 도감 1 - 시간")
st.markdown(
    "일별 박스오피스 데이터를 바탕으로 시간의 흐름에 따른 영화 관객 수 변화를 시각화합니다."
)
st.divider()

# 데이터 불러오기
try:
    df = load_data()

    # ==========================================
    # 구역 1: 영화별 일관객 변화
    # ==========================================
    st.header("1. 영화별 일관객 추이")

    # 영화 목록 추출 (관객 수 많은 순으로 정렬하여 선택 편의 제공)
    top_movies = (
        df.groupby("영화명")["일관객"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    # 영화 선택 드롭다운
    selected_movie = st.selectbox(
        "분석할 영화를 선택하세요:",
        options=top_movies,
        index=0,
    )

    # 선택한 영화 데이터 필터링
    movie_df = (
        df[df["영화명"] == selected_movie].sort_values("날짜").reset_index(drop=True)
    )

    # Plotly 선 그래프 생성
    fig1 = px.line(
        movie_df,
        x="날짜",
        y="일관객",
        title=f"[{selected_movie}] 일별 관객 수 변화",
        labels={"날짜": "날짜", "일관객": "일 관객 수 (명)"},
        markers=True,
    )

    # 마우스 오버(Hover) 툴팁 설정
    fig1.update_traces(
        hovertemplate="<b>날짜:</b> %{x|%Y-%m-%d}<br><b>일관객:</b> %{y:,.0f}명<extra></extra>"
    )
    fig1.update_layout(xaxis_title="날짜", yaxis_title="일관객 수")

    # 그래프 출력
    st.plotly_chart(fig1, use_container_width=True)

    # 인사이트 문구 자리
    st.caption(
        f"💡 **이 그래프로 알 수 있는 것:** {selected_movie}의 개봉 초기 관객 집중도와 흥행 유지 기간을 한눈에 확인할 수 있습니다."
    )

    st.divider()

    # ==========================================
    # 구역 2: (추가 예정 구역 예시)
    # ==========================================
    st.header("2. 일별 전체 관객 수 흐름 (추가 구역)")
    st.info(
        "💡 새로운 시간 관련 그래프가 들어올 구역입니다. (예: 월별 박스오피스 총관객 수, 요일별 관객 비율 등)"
    )

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
