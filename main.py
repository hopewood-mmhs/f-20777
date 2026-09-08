import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 기본 설정
st.set_page_config(
    page_title="영화 데이터 그래프 도감 1 - 시간",
    page_icon="🎬",
    layout="wide"
)

# 메인 타이틀
st.title("🎬 영화 데이터 그래프 도감 1 - 시간")
st.markdown("1년치(365일) 일별 박스오피스 데이터를 바탕으로 시간의 흐름에 따른 영화 관객 수 변화 및 추세를 시각화합니다.")

# 데이터 로드 및 전처리 (캐싱 활용)
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"
    df = pd.read_csv(url)
    
    # '날짜' 열을 문자열로 변환 후 datetime 객체로 변환 (YYYYMMDD 형식)
    df['날짜'] = pd.to_datetime(df['날짜'].astype(str), format='%Y%m%d')
    
    # 숫자형 데이터 타입 보장
    numeric_cols = ['순위', '일관객', '누적관객', '스크린수', '상영횟수']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

try:
    df = load_data()
    
    st.sidebar.header("📌 메뉴 / 설정")
    st.sidebar.info("추후 새로운 시간 관련 그래프가 이 도감에 지속적으로 추가될 예정입니다.")
    
    # 구분선
    st.divider()

    # ---------------------------------------------------------
    # 구역 1: 영화별 일관객수 추이 분석
    # ---------------------------------------------------------
    st.header("1. 영화별 일별 관객수 변화 추이")
    st.caption("특정 영화를 선택하여 상영 기간 동안의 일별 관객 수 추이를 확인합니다.")

    # 영화 목록 추출 (관객수 많은 순으로 정렬)
    movie_list = df.groupby('영화명')['누적관객'].max().sort_values(ascending=False).index.tolist()

    # 셀렉트박스 (기본값: 가장 누적관객이 많은 영화)
    selected_movie = st.selectbox(
        "📊 조회할 영화를 선택하세요:",
        options=movie_list,
        index=0
    )

    # 선택된 영화 데이터 필터링
    movie_df = df[df['영화명'] == selected_movie].sort_values('날짜')

    if not movie_df.empty:
        # Plotly 선 그래프 생성
        fig1 = px.line(
            movie_df,
            x='날짜',
            y='일관객',
            title=f"<b>[{selected_movie}]</b> 일별 관객 수 변화",
            labels={'날짜': '날짜', '일관객': '일별 관객 수(명)'},
            markers=True,
            hover_data={
                '날짜': '|%Y-%m-%d',
                '일관객': ':,d',
                '순위': True,
                '상영횟수': ':,d'
            }
        )
        
        # 그래프 스타일링
        fig1.update_traces(
            line_color='#E50914',
            line_width=2.5,
            marker=dict(size=6),
            hovertemplate="<b>날짜:</b> %{x|%Y-%m-%d}<br><b>일관객:</b> %{y:,}명<br><b>순위:</b> %{customdata[0]}위<br><b>상영횟수:</b> %{customdata[1]:,}회<extra></extra>"
        )
        
        fig1.update_layout(
            hovermode="x unified",
            xaxis_title="날짜",
            yaxis_title="일관객 수 (명)",
            margin=dict(l=20, r=20, t=50, b=20),
            template="plotly_white"
        )

        # Plotly 차트 출력
        st.plotly_chart(fig1, use_container_width=True)

        # 인사이트 문구 영역
        st.info(f"💡 **이 그래프로 알 수 있는 것:** '{selected_movie}'은(는) 상영 기간 동안 최대 {movie_df['일관객'].max():,}명의 일관객을 기록하였으며, 개봉 초기의 관객집중도 및 주말/평일 간의 관객 수 변동 주기를 파악할 수 있습니다.")
    else:
        st.warning("선택한 영화의 데이터가 존재하지 않습니다.")

    # ---------------------------------------------------------
    # 구역 2: (추가 예정 구역 예시)
    # ---------------------------------------------------------
    st.divider()
    st.header("2. [추가 예정] 월별/요일별 관객 트렌드 분석")
    st.container().write("🔒 *이 구역에는 시간의 흐름에 따른 추가 분석 그래프가 추가될 예정입니다.*")

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
