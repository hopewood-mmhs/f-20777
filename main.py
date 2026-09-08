import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 페이지 기본 설정 (타이틀, 레이아웃)
st.set_page_config(page_title="어제 박스오피스", layout="wide")

# 1. 한국 시간 기준 '어제' 날짜 계산 함수
def get_yesterday_string():
    # 한국 시간대(KST) 지정
    kst_tz = pytz.timezone('Asia/Seoul')
    # 현재 한국 시간 가져오기
    now_kst = datetime.now(kst_tz)
    # 하루(1일)를 빼서 어제 날짜 계산
    yesterday = now_kst - timedelta(days=1)
    # YYYYMMDD 형식의 문자열로 변환 (예: 20260907)
    return yesterday.strftime('%Y%m%d')

# 2. KOBIS API호출 및 캐싱 함수
# ttl=3600: 같은 날짜 데이터는 1시간(3600초) 동안 재요청하지 않고 기억(캐싱)함
@st.cache_data(ttl=3600)
def fetch_box_office_data(target_date):
    # 비밀 금고(st.secrets)에서 API 키 불러오기
    api_key = st.secrets.get("KOBIS_KEY")
    
    # API 키가 설정되지 않은 경우 예외 처리
    if not api_key:
        return None, "Secrets에 'KOBIS_KEY'가 설정되지 않았습니다. Secrets 설정을 확인해 주세요."

    # API 요청 URL 및 파라미터 설정
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": api_key,
        "targetDt": target_date
    }
    
    try:
        # API 데이터 요청 (타임아웃 10초 설정)
        response = requests.get(url, params=params, timeout=10)
        # 네트워크 오류(404, 500 등) 체크
        response.raise_for_status()
        data = response.json()
        
        # 1) API 오류 응답 처리 (인증키 오류 시 200 상태코드로 faultInfo가 반환됨)
        if "faultInfo" in data:
            error_msg = data["faultInfo"].get("message", "알 수 없는 오류가 발생했습니다.")
            return None, f"KOBIS API 오류가 발생했습니다: {error_msg} (인증키를 확인해 주세요)"
        
        # 2) 정상 응답 내 박스오피스 목록 추출
        box_office_result = data.get("boxOfficeResult", {})
        daily_list = box_office_result.get("dailyBoxOfficeList", [])
        
        # 목록이 비어있는 경우
        if not daily_list:
            return None, "조회된 박스오피스 데이터가 없습니다. 해당 날짜의 집계가 아직 완료되지 않았을 수 있습니다."
            
        return daily_list, None

    except requests.exceptions.RequestException as e:
        # 네트워크 요청 실패 시 안내
        return None, f"서버 통신에 실패했습니다. 네트워크 상태를 확인해 주세요. (상세: {e})"

# --- 메인 UI 영역 ---

# 어제 날짜 구하기 및 화면 표시용 포맷팅
yesterday_str = get_yesterday_string()
formatted_date = f"{yesterday_str[:4]}년 {yesterday_str[4:6]}월 {yesterday_str[6:]}일"

st.title("🎬 어제의 일별 박스오피스")
st.caption(f"기준 날짜(한국 시간): **{formatted_date}**")

# API 데이터 불러오기
raw_data, error_message = fetch_box_office_data(yesterday_str)

# 오류가 있는 경우 사용자 친화적인 안내 메시지 출력
if error_message:
    st.error(error_message)
    st.info("""
    💡 **확인해 보세요:**
    - Streamlit Cloud의 **Secrets** 항목에 `KOBIS_KEY`가 바르게 등록되어 있나요?
    - KOBIS 영화관입장권통합전산망에서 발급받은 API 키가 유효한가요?
    - 오늘 새벽일 경우, 어제 데이터 집계가 아직 완료되지 않았을 수 있습니다.
    """)
else:
    # 3. 데이터 전처리 (판다스 데이터프레임 변환)
    df = pd.DataFrame(raw_data)
    
    # 문자열 숫자를 정수(int)형으로 변환
    numeric_columns = ['rank', 'audiCnt', 'audiAcc', 'scrnCnt']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
    # 순위 기준으로 정렬
    df = df.sort_values(by='rank', ascending=True)

    # 4. 1위 영화 주요 지표 카드(Metric Card) 표시
    top_1 = df.iloc[0]
    st.subheader(f"🥇 1위: {top_1['movieNm']}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("일별 관객수", f"{top_1['audiCnt']:,} 명")
    col2.metric("누적 관객수", f"{top_1['audiAcc']:,} 명")
    col3.metric("스크린수", f"{top_1['scrnCnt']:,} 개")

    st.divider()

    # 5. 관객수 상위 5개 영화 막대그래프
    st.subheader("📊 관객수 Top 5 영화")
    top5_df = df.head(5)
    
    # 막대그래프 시각화 (영화명: X축, 당일 관객수: Y축)
    st.bar_chart(
        data=top5_df,
        x='movieNm',
        y='audiCnt',
        use_container_width=True
    )

    st.divider()

    # 6. 전체 박스오피스 순위표 표시
    st.subheader("📋 전체 순위 목록")
    
    # 표에 보여줄 컬럼 선택 및 이름 변경
    display_df = df[['rank', 'movieNm', 'openDt', 'audiCnt', 'audiAcc', 'scrnCnt']].copy()
    display_df.columns = ['순위', '영화명', '개봉일', '당일 관객수', '누적 관객수', '스크린수']

    # 표 출력 (숫자 세자리마다 콤마 포맷팅 적용)
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
