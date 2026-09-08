import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 0. Page Config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KOBIS 박스오피스 EDA 대시보드",
    page_icon="🎬",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. API Helper & Data Preprocessing
# -----------------------------------------------------------------------------
KOBIS_KEY = st.secrets.get("KOBIS_KEY", "")

@st.cache_data(ttl=3600)
def fetch_kobis_daily(target_date_str):
    """지정한 날짜(YYYYMMDD)의 일별 박스오피스 데이터 가져오기"""
    url = "http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": KOBIS_KEY,
        "targetDt": target_date_str
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        daily_list = data['boxOfficeResult']['dailyBoxOfficeList']
        df = pd.DataFrame(daily_list)
        return df
    except Exception:
        return pd.DataFrame()

def preprocess_boxoffice(df):
    """박스오피스 데이터 전처리 및 EDA 파생 지표 계산"""
    if df.empty:
        return df
    
    # 수치형 데이터 변환
    numeric_cols = ['audiCnt', 'audiAcc', 'scrnCnt', 'showCnt', 'salesAmt', 'salesShare']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # 파생 지표 1: 스크린 점유율 (%) (상위 10개 영화의 총 스크린 수 대비 비율)
    total_screens = df['scrnCnt'].sum()
    df['screenShare'] = (df['scrnCnt'] / total_screens * 100) if total_screens > 0 else 0
    
    # 파생 지표 2: 스크린 효율성 지수 (관객/매출 점유율 ÷ 스크린 점유율)
    df['screenEfficiency'] = df.apply(
        lambda r: round(r['salesShare'] / r['screenShare'], 2) if r['screenShare'] > 0 else 0, axis=1
    )
    
    # 파생 지표 3: 상영 1회당 평균 관객 수 (회당 알짜배기 관객 동원력)
    df['audiPerShow'] = df.apply(
        lambda r: round(r['audiCnt'] / r['showCnt'], 1) if r['showCnt'] > 0 else 0, axis=1
    )
    
    return df

# -----------------------------------------------------------------------------
# 2. Sidebar Layout
# -----------------------------------------------------------------------------
st.sidebar.title("🎬 박스오피스 EDA")
st.sidebar.markdown("---")

# 기본 선택일 (KOBIS API 특성상 전일 데이터가 최신)
default_date = datetime.now().date() - timedelta(days=1)
selected_date = st.sidebar.date_input("기준 날짜 선택", value=default_date, max_value=default_date)
target_dt_str = selected_date.strftime("%Y%m%d")

# 전주 동일 요일 날짜 계산
prev_week_date = selected_date - timedelta(days=7)
prev_week_dt_str = prev_week_date.strftime("%Y%m%d")

# -----------------------------------------------------------------------------
# 3. Data Ingestion & Processing
# -----------------------------------------------------------------------------
df_today = preprocess_boxoffice(fetch_kobis_daily(target_dt_str))
df_prev_week = preprocess_boxoffice(fetch_kobis_daily(prev_week_dt_str))

if df_today.empty:
    st.error(f"❌ {selected_date}의 박스오피스 데이터를 불러올 수 없습니다. API 키 및 날짜를 확인해 주세요.")
    st.stop()

# -----------------------------------------------------------------------------
# 4. Top KPI Section
# -----------------------------------------------------------------------------
st.title(f"📊 {selected_date.strftime('%Y년 %m월 %d일')} 박스오피스 EDA 대시보드")
st.markdown("---")

# KPI 지표 산출
total_audi_today = int(df_today['audiCnt'].sum())
top1_movie = df_today.iloc[0]
top1_share = top1_movie['salesShare']

# 전주 대비 증감률 계산
total_audi_prev = int(df_prev_week['audiCnt'].sum()) if not df_prev_week.empty else 0
if total_audi_prev > 0:
    audi_growth_rate = ((total_audi_today - total_audi_prev) / total_audi_prev) * 100
    growth_str = f"{audi_growth_rate:+.1f}% (전주 대비)"
else:
    growth_str = "전주 데이터 없음"

# 최고 스크린 효율작
max_eff_row = df_today.loc[df_today['screenEfficiency'].idxmax()]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🍿 오늘의 총 관객 수",
        value=f"{total_audi_today:,} 명",
        delta=growth_str if "전주 데이터 없음" not in growth_str else None
    )

with col2:
    st.metric(
        label="🥇 1위 영화 점유율",
        value=f"{top1_share:.1f}%",
        delta=f"{top1_movie['movieNm']}"
    )

with col3:
    st.metric(
        label="📈 전주 대비 관객 증감률",
        value=f"{audi_growth_rate:+.1f}%" if total_audi_prev > 0 else "N/A",
        delta_color="normal"
    )

with col4:
    st.metric(
        label="⚡ 최고 스크린 효율작",
        value=f"{max_eff_row['movieNm']}",
        delta=f"효율 지수: {max_eff_row['screenEfficiency']}"
    )

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. Main Interactive Charts Section
# -----------------------------------------------------------------------------
st.subheader("📈 메인 데이터 탐색 & 트렌드 리포트")

chart_tab1, chart_tab2 = st.tabs(["점유율 vs 스크린 효율성 (Scatter)", "상위 영화 관객 수 / 스크린 비교"])

with chart_tab1:
    # Scatter plot: 스크린 점유율 vs 관객 점유율 (대각선 위쪽에 위치할수록 효율이 뛰어남)
    fig_eff = px.scatter(
        df_today,
        x="screenShare",
        y="salesShare",
        size="audiCnt",
        color="movieNm",
        text="movieNm",
        labels={"screenShare": "스크린 점유율 (%)", "salesShare": "관객(매출) 점유율 (%)"},
        title="<b>스크린 점유율 대비 관객 점유율 (버블 크기 = 관객 수)</b>",
        hover_data=["rank", "scrnCnt", "audiCnt", "screenEfficiency", "audiPerShow"]
    )
    # 1:1 대각선 기준선 추가
    fig_eff.add_shape(
        type="line", line=dict(dash="dash", color="gray"),
        x0=0, x1=df_today['screenShare'].max(),
        y0=0, y1=df_today['screenShare'].max()
    )
    fig_eff.update_traces(textposition='top center')
    st.plotly_chart(fig_eff, use_container_width=True)

with chart_tab2:
    # Bar Chart: 관객 수 및 스크린 수 이중 축 비교
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=df_today['movieNm'], y=df_today['audiCnt'],
        name="일별 관객 수 (명)", marker_color="royalblue"
    ))
    fig_bar.add_trace(go.Bar(
        x=df_today['movieNm'], y=df_today['scrnCnt'],
        name="스크린 수 (개)", marker_color="lightslategrey"
    ))
    fig_bar.update_layout(
        title="<b>영화별 일별 관객 수 vs 보유 스크린 수</b>",
        barmode="group",
        xaxis_title="영화명",
        yaxis_title="수량"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. Detailed Data Grid Section
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 하단 분석 데이터 테이블")

grid_df = df_today[[
    'rank', 'movieNm', 'openDt', 'audiCnt', 'audiAcc', 
    'scrnCnt', 'showCnt', 'salesShare', 'screenEfficiency', 'audiPerShow'
]].copy()

grid_df.columns = [
    '순위', '영화명', '개봉일', '일별 관객수', '누적 관객수',
    '스크린 수', '상영 횟수', '관객 점유율(%)', '스크린 효율 지수', '회당 평균 관객'
]

st.dataframe(
    grid_df,
    column_config={
        "순위": st.column_config.NumberColumn(format="%d"),
        "일별 관객수": st.column_config.NumberColumn(format="%d 명"),
        "누적 관객수": st.column_config.NumberColumn(format="%d 명"),
        "스크린 수": st.column_config.NumberColumn(format="%d 개"),
        "상영 횟수": st.column_config.NumberColumn(format="%d 회"),
        "관객 점유율(%)": st.column_config.NumberColumn(format="%.1f%%"),
        "스크린 효율 지수": st.column_config.NumberColumn(
            format="%.2f",
            help="1보다 크면 스크린 배정 대비 흥행 효율이 뛰어남을 의미합니다."
        ),
        "회당 평균 관객": st.column_config.NumberColumn(
            format="🍿 %.1f 명",
            help="상영 1회당 들어온 평균 관객 수입니다."
        )
    },
    use_container_width=True,
    hide_index=True
)
