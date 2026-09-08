import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="날짜별 박스오피스", layout="wide")

# 1. 한국 시간 기준 '어제' Date 객체 구하기 함수
def get_yesterday_date():
    kst_tz = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst_tz)
    yesterday = now_kst - timedelta(days=1)
    return yesterday.date()

# 2. KOBIS API 호출 및 캐싱 함수
# 입력받은 target_date(YYYYMMDD) 기준으로 1시간 캐싱
@st.cache_data(ttl=3600)
def fetch_box_office_data(target_date_str):
    api_key = st.secrets.get("KOBIS_KEY")
    
    if not api_key:
        return None, "Secrets에 'KOBIS_KEY'가 설정되지 않았습니다. Secrets 설정을 확인해 주세요."

    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": api_key,
        "targetDt": target_date_str
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # API 오류 응답 처리
        if "faultInfo" in data:
            error_msg = data["faultInfo"].get("message", "알 수 없는 오류가 발생했습니다.")
            return None, f"KOBIS API 오류가 발생했습니다: {error_msg} (인증키를 확인해 주세요)"
        
        box_office_result = data.get("boxOfficeResult", {})
        daily_list = box_office_result.get("dailyBoxOfficeList", [])
        
        # 목록이 비어있는 경우
        if not daily_list:
            return None, "선택하신 날짜는 아직 집계 전이거나 데이터가 없습니다."
            
        return daily_list, None

    except requests.exceptions.RequestException as e:
        return None, f"서버 통신에 실패했습니다. 네트워크 상태를 확인해 주세요. (상세: {e})"

# --- 메인 UI 영역 ---

st.title("🎬 날짜별 박스오피스 조회")

# 3. 날짜 선택기 (Date Input)
yesterday_date = get_yesterday_date()

# 사이드바 또는 메인 화면 상단에 날짜 선택 달력 배치
selected_date = st.date_input(
    "조회할 날짜를 선택하세요 (최대: 어제)",
    value=yesterday_date,
    max_value=yesterday_date,  # 오늘 이후 날짜는 선택 불가
    min_value=datetime(2004, 1, 1).date() # KOBIS 데이터 제공 시작 시점 근처
)

# 선택한 날짜를 YYYYMMDD 문자열로 변환
target_date_str = selected_date.strftime('%Y%m%d')
formatted_date = selected_date.strftime('%Y년 %m월 %d일')

st.caption(f"선택된 조회 날짜: **{formatted_date}**")

# API 데이터 불러오기
raw_data, error_message = fetch_box_office_data(target_date_str)

# 오류 메시지 또는 집계 전 안내
if error_message:
    st.warning(error_message)
    st.info("""
    💡 **참고 사항:**
    - KOBIS 박스오피스는 보통 다음 날 새벽~아침 사이에 집계가 완료됩니다.
    - 입력 키(`KOBIS_KEY`)가 정상인지 확인해 주세요.
    """)
else:
    # 4. 데이터 전처리
    df = pd.DataFrame(raw_data)
    
    # 숫자로 사용할 컬럼들 정수형 변환
    numeric_columns = ['rank', 'rankInten', 'audiCnt', 'audiAcc', 'scrnCnt']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
    # 순위 기준으로 정렬
    df = df.sort_values(by='rank', ascending=True)

    # 5. 순위 변동(rankInten) 및 100만 관객 이모지 가공 함수 적용
    def format_rank_change(val):
        if val > 0:
            return f"🔺 +{val}"  # 상승 (빨간 위 화살표)
        elif val < 0:
            return f"🔹 {val}"   # 하락 (파란 아래 화살표)
        else:
            return "-"           # 변동 없음

    df['rankChange'] = df['rankInten'].apply(format_rank_change)

    # 누적관객 100만 명 이상일 경우 영화명에 🏆 이모지 추가
    df['displayMovieNm'] = df.apply(
        lambda row: f"🏆 {row['movieNm']}" if row['audiAcc'] >= 1_000_000 else row['movieNm'],
        axis=1
    )

    # 6. 1위 영화 주요 지표 카드
    top_1 = df.iloc[0]
    st.subheader(f"🥇 1위: {top_1['displayMovieNm']}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("일별 관객수", f"{top_1['audiCnt']:,} 명")
    col2.metric("누적 관객수", f"{top_1['audiAcc']:,} 명")
    col3.metric("스크린수", f"{top_1['scrnCnt']:,} 개")

    st.divider()

    # 7. 관객수 상위 5개 영화 막대그래프
    st.subheader("📊 관객수 Top 5 영화")
    top5_df = df.head(5)
    
    st.bar_chart(
        data=top5_df,
        x='movieNm',  # 그래프 축에는 트로피 없는 깔끔한 원래 이름 사용
        y='audiCnt',
        use_container_width=True
    )

    st.divider()

    # 8. 전체 박스오피스 순위표 표시
    st.subheader("📋 전체 순위 목록")
    
    # 표에 보여줄 컬럼 선택 및 순서 정리
    display_df = df[['rank', 'rankChange', 'displayMovieNm', 'openDt', 'audiCnt', 'audiAcc', 'scrnCnt']].copy()
    display_df.columns = ['순위', '전일대비', '영화명', '개봉일', '당일 관객수', '누적 관객수', '스크린수']

    # 표 출력
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "당일 관객수": st.column_config.NumberColumn(format="%d명"),
            "누적 관객수": st.column_config.NumberColumn(format="%d명"),
            "스크린수": st.column_config.NumberColumn(format="%d개"),
        }
    )
