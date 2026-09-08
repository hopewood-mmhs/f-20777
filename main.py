import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="1년치 박스오피스 분석기", layout="wide")

# -------------------------------------------------------------------
# [1] API 키 불러오기 및 기본 처리
# Streamlit secrets에서 KOBIS_KEY를 가져옵니다.
# -------------------------------------------------------------------
try:
    API_KEY = st.secrets["KOBIS_KEY"]
except Exception:
    API_KEY = None

st.title("🎬 KOBIS 1년치 박스오피스 데이터 분석")

# API 키가 등록되지 않았을 때 사용자에게 안내 문구를 띄웁니다.
if not API_KEY:
    st.error("⚠️ API 키를 넣어주세요. (.streamlit/secrets.toml 파일에 KOBIS_KEY를 설정해야 합니다.)")
    st.stop()


# -------------------------------------------------------------------
# [2] 1년치 박스오피스 데이터 수집 함수 (캐싱 적용)
# @st.cache_data를 사용하여 이미 가져온 데이터는 재요청 없이 기억해둡니다.
# -------------------------------------------------------------------
@st.cache_data(ttl=86400 * 30) # 한 번 가져온 데이터는 한 달간 재사용합니다.
def fetch_one_year_boxoffice(api_key):
    # 서버 시계와 상관없이 한국 표준시(KST) 기준으로 날짜를 계산합니다.
    tz_kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(tz_kst)
    
    # '어제' 날짜를 구합니다 (오늘 데이터는 집계 전이므로 어제부터 시작)
    yesterday = now_kst - timedelta(days=1)
    
    # 어제부터 과거 365일간의 날짜 목록(YYYYMMDD 형태)을 생성합니다.
    date_list = [(yesterday - timedelta(days=i)).strftime('%Y%m%d') for i in range(365)]
    
    all_data = [] # 모든 일자별 영화 데이터를 담을 리스트
    failed_dates = [] # 데이터를 불러오지 못한 날짜를 담을 리스트
    
    # 화면에 수집 진행 상황을 보여주는 바(Bar)와 텍스트를 준비합니다.
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_days = len(date_list)
    
    base_url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    
    # 365일 데이터를 하루씩 반복해서 가져옵니다.
    for index, target_dt in enumerate(date_list):
        # 진행 상황 안내 문구 업데이트
        status_text.text(f"⏳ 데이터 수집 중... ({index + 1}/{total_days} 일) - 기준일자: {target_dt}")
        progress_bar.progress((index + 1) / total_days)
        
        try:
            params = {
                'key': api_key,
                'targetDt': target_dt
            }
            # API 요청 보내기 (타임아웃 10초 설정)
            response = requests.get(base_url, params=params, timeout=10)
            
            # 네트워크 요청 실패 시 해당 날짜 건너뛰기
            if response.status_code != 200:
                failed_dates.append(target_dt)
                continue
            
            data = response.json()
            
            # API 내부 에러(faultInfo)가 포함되어 있는 경우 건너뛰기
            if 'faultInfo' in data:
                failed_dates.append(target_dt)
                continue
                
            box_office_result = data.get('boxOfficeResult', {})
            daily_list = box_office_result.get('dailyBoxOfficeList', [])
            
            # 영화 목록이 비어있는 경우 건너뛰기
            if not daily_list:
                failed_dates.append(target_dt)
                continue
            
            # 추출한 각 영화 정보에 '조회 날짜' 정보를 추가하여 저장
            for movie in daily_list:
                movie['targetDt'] = target_dt
                all_data.append(movie)
                
        except Exception:
            # 에러 발생 시 해당 날짜를 failure에 기록하고 계속 진행
            failed_dates.append(target_dt)
            continue

    # 작업 완료 후 진행 표시줄 숨기기
    progress_bar.empty()
    status_text.empty()
    
    # 수집된 데이터를 판다스 데이터프레임으로 변환
    df = pd.DataFrame(all_data)
    
    # ---------------------------------------------------------------
    # [3] 데이터 전처리 (숫자형으로 변환)
    # API에서 문자열로 넘어온 숫자 데이터를 실제 숫자형으로 바꿔줍니다.
    # ---------------------------------------------------------------
    if not df.empty:
        numeric_columns = ['rank', 'rankInten', 'audiCnt', 'audiAcc', 'scrnCnt', 'showCnt']
        for col in numeric_columns:
            if col in df.columns:
                # 숫자로 변환할 수 없는 값은 NaN(빈값) 처리 후 0으로 채움
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
    return df, failed_dates


# -------------------------------------------------------------------
# [4] 화면 구성 및 데이터 로드 실행
# -------------------------------------------------------------------
st.subheader("📊 데이터 수집 및 조회")

# 데이터 불러오기 버튼
if st.button("🚀 1년치 데이터 수집 시작"):
    df, failed_dates = fetch_one_year_boxoffice(API_KEY)
    
    # 가져온 데이터프레임을 세션 상태에 저장하여 화면에 유지
    st.session_state['df'] = df
    st.session_state['failed_dates'] = failed_dates

# 수집 완료 후 결과 표시
if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
    failed_dates = st.session_state['failed_dates']
    
    st.success(f"데이터 수집이 완료되었습니다! (총 {len(df):,}개 행 수집 완료)")
    
    # 누락/실패된 날짜가 있다면 한국어로 안내
    if failed_dates:
        st.warning(f"⚠️ 총 {len(failed_dates)}개의 날짜 데이터를 가져오지 못했습니다. (실패 일자 수: {len(failed_dates)}일)")
    else:
        st.info("🎉 모든 날짜(365일)의 데이터를 성공적으로 가져왔습니다!")

    # ---------------------------------------------------------------
    # [5] 팝업(다이얼로그) 형태의 데이터프레임 확인 버튼
    # ---------------------------------------------------------------
    @st.dialog("📋 1년치 전체 박스오피스 데이터", width="large")
    def show_data_dialog():
        st.write("문자열 숫자가 모두 실제 숫자형(Int/Float)으로 정제된 데이터입니다.")
        st.dataframe(df, use_container_width=True)

    if st.button("🔍 데이터프레임 새 창(팝업)으로 보기"):
        show_data_dialog()

# -------------------------------------------------------------------
# [6] 그래프 자리(틀) 미리 만들어두기 (그래프 1 ~ 그래프 5)
# -------------------------------------------------------------------
st.write("---")
st.subheader("📈 시각화 영역 (시각화 준비 공간)")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("### 📌 그래프 1")
        st.info("여기에 첫 번째 그래프가 들어갈 자리입니다.")

    with st.container(border=True):
        st.markdown("### 📌 그래프 3")
        st.info("여기에 세 번째 그래프가 들어갈 자리입니다.")

    with st.container(border=True):
        st.markdown("### 📌 그래프 5")
        st.info("여기에 다섯 번째 그래프가 들어갈 자리입니다.")

with col2:
    with st.container(border=True):
        st.markdown("### 📌 그래프 2")
        st.info("여기에 두 번째 그래프가 들어갈 자리입니다.")

    with st.container(border=True):
        st.markdown("### 📌 그래프 4")
        st.info("여기에 네 번째 그래프가 들어갈 자리입니다.")
