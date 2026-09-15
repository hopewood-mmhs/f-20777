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

# ----------------------------------------------------
# 3번 그래프: 총 관객 수 분포 (히스토그램)
# ----------------------------------------------------
st.subheader("3. 영화별 총 관객 수 분포")

# Plotly 히스토그램 생성
fig3 = px.histogram(
    df,
    x="total_audi",
    nbins=25,
    title="총 관객 수 히스토그램",
    labels={"total_audi": "총 관객 수"},
)

fig3.update_traces(
    hovertemplate="<b>관객 수 구간</b>: %{x:,.0f}명<br><b>영화 수</b>: %{y}편"
)

fig3.update_layout(
    xaxis_title="총 관객 수 (명)",
    yaxis_title="영화 수 (편)",
)

# 그래프 출력
st.plotly_chart(fig3, use_container_width=True)

# 데이터 기반 최다 관객 영화 자동 추출
top_movie = df.loc[df["total_audi"].idxmax()]
top_movie_name = top_movie["movieNm"]
top_movie_audi = top_movie["total_audi"]

# 그래프 해석 구역
with st.container():
    st.markdown("**💡 이 그래프로 알 수 있는 것**")
    st.info(
        f"대부분의 영화는 초반 저관객 구간(약 100만~300만 명 이하)에 빽빽하게 몰려 있으며, "
        f"가장 관객이 많은 영화는 **'{top_movie_name}'**(총 {top_movie_audi:,.0f}명)입니다."
    )

st.markdown("---")

# ----------------------------------------------------
# 4번 그래프: 개봉일 스크린수 vs 총 관객수 (산점도)
# ----------------------------------------------------
st.subheader("4. 개봉일 스크린 수와 총 관객 수의 관계")

# Plotly 산점도 생성
fig4 = px.scatter(
    df,
    x="first_scrn",
    y="total_audi",
    color="genre",
    hover_name="movieNm",
    title="개봉일 스크린 수 vs 총 관객 수",
    labels={
        "first_scrn": "개봉일 스크린 수",
        "total_audi": "총 관객 수",
        "genre": "장르",
    },
)

# 마우스 오버 시 정보 레이아웃 설정
fig4.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>개봉일 스크린 수: %{x:,.0f}개<br>총 관객 수: %{y:,.0f}명"
)

fig4.update_layout(
    xaxis_title="개봉일 스크린 수 (개)",
    yaxis_title="총 관객 수 (명)",
)

# 그래프 출력
st.plotly_chart(fig4, use_container_width=True)

# 그래프 해석 구역
with st.container():
    st.markdown("**💡 이 그래프로 알 수 있는 것**")
    st.info(
        "개봉일 스크린 수가 많을수록 대체로 총 관객 수가 증가하는 양의 상관관계를 보이나, "
        "초기 스크린 수 대비 극단적으로 높거나 낮은 성과를 낸 아웃라이어 영화들도 함께 확인할 수 있습니다."
    )

st.markdown("---")

# ----------------------------------------------------
# 5번 그래프: 주요 장르별 총 관객 수 분포 (박스플롯)
# ----------------------------------------------------
st.subheader("5. 주요 장르별 총 관객 수 상자 그림 (영화 10편 이상 장르)")

# 영화가 10편 이상인 장르만 필터링
genre_counts_all = df["genre"].value_counts()
major_genres = genre_counts_all[genre_counts_all >= 10].index
df_major_genres = df[df["genre"].isin(major_genres)]

# Plotly 박스플롯 생성
fig5 = px.box(
    df_major_genres,
    x="genre",
    y="total_audi",
    color="genre",
    hover_name="movieNm",
    points="outliers",  # 이상치(상자 밖 튀는 점) 표시
    title="10편 이상 제작된 주요 장르별 관객 수 분포",
    labels={"genre": "장르", "total_audi": "총 관객 수"},
)

# 마우스 오버 시 영화명과 관객 수 정보가 잘 표시되도록 설정
fig5.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>총 관객 수: %{y:,.0f}명"
)

fig5.update_layout(
    xaxis_title="장르",
    yaxis_title="총 관객 수 (명)",
    showlegend=False,  # x축이 장르이므로 범례 숨김
)

# 그래프 출력
st.plotly_chart(fig5, use_container_width=True)

# 그래프 해석 구역
with st.container():
    st.markdown("**💡 이 그래프로 알 수 있는 것**")
    st.info(
        "주요 장르별 관객 수의 중앙값과 편차 범위(IQR)를 비교할 수 있으며, "
        "상자 밖의 점(이상치)을 통해 해당 장르에서 초대형 흥행을 이끌어낸 히트작 영화들을 한눈에 식별할 수 있습니다."
    )

st.markdown("---")

# ----------------------------------------------------
# 6번 그래프: 개봉일 스크린수 vs 총 관객수 (버블 차트 - 첫 주 관객수 크기)
# ----------------------------------------------------
st.subheader("6. 개봉일 스크린 수 vs 총 관객 수 (첫 주 관객 수 버블 차트)")

# Plotly 버블 차트 생성
fig6 = px.scatter(
    df,
    x="first_scrn",
    y="total_audi",
    size="first_week_audi",
    color="genre",
    hover_name="movieNm",
    size_max=40,
    title="개봉일 스크린 수 vs 총 관객 수 (버블 크기 = 개봉 첫 주 관객 수)",
    labels={
        "first_scrn": "개봉일 스크린 수",
        "total_audi": "총 관객 수",
        "first_week_audi": "개봉 첫 주 관객 수",
        "genre": "장르",
    },
)

# 마우스 오버 시 정보 레이아웃 설정
fig6.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>개봉일 스크린 수: %{x:,.0f}개<br>총 관객 수: %{y:,.0f}명<br>개봉 첫 주 관객 수: %{marker.size:,.0f}명"
)

fig6.update_layout(
    xaxis_title="개봉일 스크린 수 (개)",
    yaxis_title="총 관객 수 (명)",
)

# 그래프 출력
st.plotly_chart(fig6, use_container_width=True)

# 그래프 해석 구역
with st.container():
    st.markdown("**💡 이 그래프로 알 수 있는 것**")
    st.info(
        "버블의 크기를 통해 개봉 초기의 폭발적인 관객 동원력을 시각적으로 함께 비교할 수 있습니다. "
        "예를 들어 초기 스크린 수는 적었지만 버블이 큰 영화는 입소문을 통해 초반 흥행에 성공했음을 알 수 있습니다."
    )

st.markdown("---")
