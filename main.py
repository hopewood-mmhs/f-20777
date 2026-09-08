# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
    st.sidebar.info("시간 관련 박스오피스 시각화 그래프 도감입니다.")
    st.divider()

    # ---------------------------------------------------------
    # 구역 1: 영화별 일관객수 추이 분석
    # ---------------------------------------------------------
    st.header("1. 영화별 일별 관객수 변화 추이")
    st.caption("특정 영화를 선택하여 상영 기간 동안의 일별 관객 수 추이를 확인합니다.")

    # 영화 목록 추출 (누적관객 많은 순 정렬)
    movie_list = df.groupby('영화명')['누적관객'].max().sort_values(ascending=False).index.tolist()

    selected_movie = st.selectbox(
        "📊 조회할 영화를 선택하세요:",
        options=movie_list,
        index=0
    )

    movie_df = df[df['영화명'] == selected_movie].sort_values('날짜')

    if not movie_df.empty:
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

        st.plotly_chart(fig1, use_container_width=True)

        st.info(f"💡 **이 그래프로 알 수 있는 것:** '{selected_movie}'은(는) 상영 기간 동안 최대 {movie_df['일관객'].max():,}명의 일관객을 기록하였으며, 개봉 초기의 관객집중도 및 주말/평일 간의 관객 수 변동 주기를 파악할 수 있습니다.")
    else:
        st.warning("선택한 영화의 데이터가 존재하지 않습니다.")

    # ---------------------------------------------------------
    # 구역 2: 기간 내 일관객 합계 Top 5 영화 비교
    # ---------------------------------------------------------
    st.divider()
    st.header("2. 기간 내 일관객 합계 Top 5 영화 일별 추이 비교")
    st.caption("1년 동안 전체 일관객 합계가 가장 큰 상위 5개 영화의 날짜별 일관객 변화를 비교합니다.")

    top5_movies = df.groupby('영화명')['일관객'].sum().nlargest(5).index.tolist()
    top5_df = df[df['영화명'].isin(top5_movies)].sort_values('날짜')

    if not top5_df.empty:
        fig2 = px.line(
            top5_df,
            x='날짜',
            y='일관객',
            color='영화명',
            title="<b>[Top 5 영화]</b> 날짜별 일관객 수 추이 비교",
            labels={'날짜': '날짜', '일관객': '일별 관객 수(명)', '영화명': '영화 제목'},
            markers=True
        )

        fig2.update_traces(
            line_width=2,
            marker=dict(size=5),
            hovertemplate="<b>영화명:</b> %{fullData.name}<br><b>날짜:</b> %{x|%Y-%m-%d}<br><b>일관객:</b> %{y:,}명<extra></extra>"
        )

        fig2.update_layout(
            hovermode="x unified",
            xaxis_title="날짜",
            yaxis_title="일관객 수 (명)",
            legend_title_text="영화 목록 (클릭하여 켜기/끄기)",
            margin=dict(l=20, r=20, t=50, b=20),
            template="plotly_white"
        )

        st.plotly_chart(fig2, use_container_width=True)

        top5_str = ", ".join([f"'{m}'" for m in top5_movies])
        st.info(f"💡 **이 그래프로 알 수 있는 것:** 1년 동안 일관객 합계가 가장 높은 상위 5개 영화({top5_str})의 흥행 시기 겹침 여부와 개봉 시기별 일관객 정점(Peak) 차이를 한눈에 비교할 수 있습니다.")
    else:
        st.warning("Top 5 영화 데이터를 생성할 수 없습니다.")

    # ---------------------------------------------------------
    # 구역 3: 날짜별 Top 10 영화 총 관객수 (영역 그래프)
    # ---------------------------------------------------------
    st.divider()
    st.header("3. 날짜별 박스오피스 Top 10 총 관객 수 추이 (영역 그래프)")
    st.caption("매일 박스오피스 Top 10 영화들의 일관객 합계를 계산하여 전체 영화 시장의 규모 변화를 시각화합니다.")

    # 일별 Top 10 관객수 합계 계산
    daily_total = df.groupby('날짜')['일관객'].sum().reset_index().sort_values('날짜')

    if not daily_total.empty:
        # 관객수가 가장 컸던 상위 3일 추출
        top3_days = daily_total.nlargest(3, '일관객')

        # Area 그래프 생성
        fig3 = px.area(
            daily_total,
            x='날짜',
            y='일관객',
            title="<b>[전체 박스오피스]</b> 날짜별 Top 10 관객 수 합계 변화",
            labels={'날짜': '날짜', '일관객': 'Top 10 총 관객 수(명)'}
        )

        fig3.update_traces(
            line_color='#008080',
            fillcolor='rgba(0, 128, 128, 0.3)',
            hovertemplate="<b>날짜:</b> %{x|%Y-%m-%d}<br><b>Top 10 총 관객:</b> %{y:,}명<extra></extra>"
        )

        # 상위 3일 붉은 다이아몬드 마커 및 날짜/관객수 텍스트 표시
        for idx, row in top3_days.iterrows():
            date_str = row['날짜'].strftime('%Y-%m-%d')
            val = row['일관객']
            
            fig3.add_trace(go.Scatter(
                x=[row['날짜']],
                y=[val],
                mode='markers+text',
                marker=dict(color='red', size=10, symbol='diamond'),
                text=[f" 🏆 Top {date_str}<br>({val:,}명)"],
                textposition="top center",
                showlegend=False,
                hoverinfo='skip'
            ))

        fig3.update_layout(
            hovermode="x unified",
            xaxis_title="날짜",
            yaxis_title="Top 10 관객 수 합계(명)",
            margin=dict(l=20, r=20, t=70, b=20),
            template="plotly_white"
        )

        st.plotly_chart(fig3, use_container_width=True)

        top3_info_str = ", ".join([f"{r['날짜'].strftime('%Y-%m-%d')} ({r['일관객']:,}명)" for _, r in top3_days.iterrows()])
        st.info(f"💡 **이 그래프로 알 수 있는 것:** 연중 극장가 전체 관객 수의 계절성(명절, 연휴, 성수기)을 파악할 수 있으며, 관객 수가 가장 많았던 상위 3일({top3_info_str})을 확인할 수 있습니다.")
    else:
        st.warning("영역 그래프 데이터를 생성할 수 없습니다.")

    # ---------------------------------------------------------
    # 구역 4: (추가 예정 구역 예시)
    # ---------------------------------------------------------
    st.divider()
    st.header("4. [추가 예정] 월별/요일별 관객 트렌드 분석")
    st.container().write("🔒 *이 구역에는 시간의 흐름에 따른 추가 분석 그래프가 추가될 예정입니다.*")

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
