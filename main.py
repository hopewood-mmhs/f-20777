import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="영화 데이터 그래프 도감 2 - 분포와 관계",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 영화 데이터 그래프 도감 2 - 분포와 관계")
st.markdown("---")


# 데이터 로드 및 전처리 함수
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"
    df = pd.read_csv(url)

    # 장르 전처리: '|'로 구분된 장르 중 첫 번째 장르만 추출
    df["genre"] = df["genre"].astype(str).str.split("|").str[0]

    return df


df = load_data()

# ----------------------------------------------------
# 1번 그래프: 장르별 영화 편수 (도넛 차트)
# ----------------------------------------------------
st.subheader("1. 장르별 영화 편수 분포")

# 장르별 빈도수 계산
genre_counts = df["genre"].value_counts().reset_index()
genre_counts.columns = ["장르", "영화 편수"]

# Plotly 도넛 그래프 생성
fig1 = px.pie(
    genre_counts,
    values="영화 편수",
    names="장르",
    hole=0.4,
    title="장르별 영화 비율",
)

# 마우스 오버 시 편수와 비율이 보이도록 설정
fig1.update_traces(
    textinfo="percent+label",
    hovertemplate="<b>장르</b>: %{label}<br><b>영화 편수</b>: %{value}편<br><b>비율</b>: %{percent}",
)

# 그래프 출력
st.plotly_chart(fig1, use_container_width=True)

# 그래프 해석 구역
with st.container():
    st.markdown("**💡 이 그래프로 알 수 있는 것**")
    st.info(
        "박스오피스 상위권 영화 중 어떤 장르가 가장 큰 비중을 차지하는지, 시장의 장르 쏠림 현상을 한눈에 파악할 수 있습니다."
    )

st.markdown("---")

# ----------------------------------------------------
# 2번 그래프: 장르 및 영화별 총 관객수 (트리맵)
# ----------------------------------------------------
st.subheader("2. 장르 및 개별 영화의 총 관객 수 분포")

# Plotly 트리맵 생성 (장르 -> 영화명 계층 구조)
fig2 = px.treemap(
    df,
    path=[px.Constant("전체 장르"), "genre", "movieNm"],
    values="total_audi",
    color="genre",
    title="장르 및 영화별 총 관객수 분포 (칸 크기 = 총 관객 수)",
)

# 마우스 오버(Hover) 시 영화명과 총 관객수가 표시되도록 설정
fig2.update_traces(
    hovertemplate="<b>영화명/카테고리</b>: %{label}<br><b>총 관객 수</b>: %{value:,.0f}명"
)

# 그래프 출력
st.plotly_chart(fig2, use_container_width=True)

# 그래프 해석 구역
with st.container():
    st.markdown("**💡 이 그래프로 알 수 있는 것**")
    st.info(
        "각 장르의 전체 흥행 규모뿐만 아니라 특정 장르 내에서 어떤 영화가 총 관객 수를 주도했는지 직관적으로 비교할 수 있습니다."
    )

st.markdown("---")
