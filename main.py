from datetime import datetime, timedelta
import zoneinfo
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide",
)


# ==========================================
# 1. API 데이터 불러오기 함수 (캐싱 적용)
# ==========================================
# st.cache_data를 이용해 동일한 target_date 요청 시 1시간(3600초) 동안 API를 다시 부르지 않고 기존 저장 결과를 사용합니다.
@st.cache_data(ttl=3600)
def fetch_daily_boxoffice(target_date: str, api_key: str):
    """KOBIS API를 호출하여 어제의 일별 박스오피스 데이터를 가져옵니다."""
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": target_date}

    try:
        # API 요청 보내기 (타임아웃 10초 설정)
        response = requests.get(url, params=params, timeout=10)

        # HTTP 응답 상태코드가 200이 아닌 경우 예외 발생
        if response.status_code != 200:
            return None, f"HTTP 요청 오류가 발생했습니다. (상태 코드: {response.status_code})"

        data = response.json()

        # [에러 처리 1] API 인증키 오류 등으로 faultInfo 상자가 반환된 경우
        if "faultInfo" in data:
            error_msg = data["faultInfo"].get(
                "message", "알 수 없는 오류가 발생했습니다."
            )
            return (
                None,
                f"KOBIS API 오류가 발생했습니다.\n안내 메세지: {error_msg}\n\n"
                "💡 **확인 사항:** Streamlit Cloud Secrets에 `KOBIS_KEY`가 올바르게 입력되었는지 확인해 주세요.",
            )

        # [에러 처리 2] 응답 구조 확인 및 영화 목록 존재 여부 검사
        boxoffice_result = data.get("boxOfficeResult", {})
        daily_list = boxoffice_result.get("dailyBoxOfficeList", [])

        if not daily_list:
            return (
                None,
                "선택한 날짜의 박스오피스 데이터가 비어 있습니다.\n\n"
                "💡 **확인 사항:** 아직 영화관입장권통합전산망(KOBIS) 데이터 집계가 완료되지 않았을 수 있습니다. 잠시 후 다시 시도해 주세요.",
            )

        # 성공 시 데이터 리스트 반환
        return daily_list, None

    except requests.exceptions.RequestException as e:
        return (
            None,
            f"네트워크 통신 중 오류가 발생했습니다.\n상세 내용: {e}\n\n"
            "💡 **확인 사항:** 인터넷 연결 상태를 확인하거나 KOBIS 서버 상태를 확인해 주세요.",
        )


# ==========================================
# 2. 메인 화면 및 데이터 처리
# ==========================================
def main():
    st.title("🎬 어제의 일별 박스오피스")

    # [Secrets 확인] 비밀 금고(Secrets)에서 KOBIS_KEY 불러오기
    if "KOBIS_KEY" not in st.secrets:
        st.error(
            "🔑 **KOBIS_KEY가 설정되지 않았습니다.**\n\n"
            "Streamlit Cloud의 App Settings -> **Secrets** 메뉴에서 다음과 같이 발급받은 API 키를 입력해 주세요:\n\n"
            '```toml\nKOBIS_KEY = "발급받은_키_문자열"\n```'
        )
        st.stop()

    api_key = st.secrets["KOBIS_KEY"]

    # [날짜 계산] 배포 서버 시계와 상관없이 한국 시간(Asia/Seoul) 기준 '어제' 날짜 구하기
    korea_tz = zoneinfo.ZoneInfo("Asia/Seoul")
    now_korea = datetime.now(korea_tz)
    yesterday = now_korea - timedelta(days=1)

    # YYYYMMDD 여덟 자리 숫자 문자열로 변환
    target_date_str = yesterday.strftime("%Y%m%d")
    display_date_str = yesterday.strftime("%Y년 %m월 %d일")

    st.markdown(f"**기준 날짜:** {display_date_str} (한국 시간 기준 어제)")
    st.divider()

    # 데이터 가져오기
    daily_list, error_message = fetch_daily_boxoffice(target_date_str, api_key)

    # 오류가 발생한 경우 안내 메시지 출력 후 정지
    if error_message:
        st.warning(error_message)
        st.stop()

    # 데이터프레임(Dataframe) 변환
    df = pd.DataFrame(daily_list)

    # [숫자 형변환] 문자열 형태의 숫자 데이터를 정수형(int)으로 변환
    numeric_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # 순위(rank) 기준으로 정렬
    df = df.sort_values("rank").reset_index(drop=True)

    # ==========================================
    # 3. 1위 영화 지표 카드 (Metric Card)
    # ==========================================
    top_1 = df.iloc[0]

    st.subheader(f"🥇 어제의 1위 영화: {top_1['movieNm']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="어제 관객 수",
            value=f"{top_1['audiCnt']:,} 명",
            delta=f"순위: {top_1['rank']}위",
        )
    with col2:
        st.metric(
            label="누적 관객 수",
            value=f"{top_1['audiAcc']:,} 명",
        )
    with col3:
        st.metric(
            label="상영 스크린 수",
            value=f"{top_1['scrnCnt']:,} 개",
        )

    st.divider()

    # ==========================================
    # 4. 관객수 상위 5편 막대그래프
    # ==========================================
    st.subheader("📊 관객수 상위 5개 영화")

    top5_df = df.head(5).copy()

    # Plotly 그래프 생성 (관객 수가 높은 영화가 위쪽에 오도록 역순 정렬)
    top5_df_sorted = top5_df.sort_values("audiCnt", ascending=True)

    fig = px.bar(
        top5_df_sorted,
        x="audiCnt",
        y="movieNm",
        orientation="h",  # 가로 막대그래프
        text="audiCnt",
        labels={"audiCnt": "일일 관객 수 (명)", "movieNm": "영화명"},
        title="어제 관객 수 Top 5",
        color="audiCnt",
        color_continuous_scale="Blues",
    )

    # 막대 안의 숫자 포맷팅 (천 단위 쉼표 추가)
    fig.update_traces(texttemplate="%{text:,}명", textposition="outside")
    fig.update_layout(
        xaxis_title="관객 수 (명)",
        yaxis_title="",
        showlegend=False,
        coloraxis_showscale=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ==========================================
    # 5. 전체 박스오피스 순위 표
    # ==========================================
    st.subheader("📋 박스오피스 전체 순위 (Top 10)")

    # 화면에 보여줄 열 선택 및 이름 변경
    display_df = df[
        ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
    ].copy()
    display_df.columns = [
        "순위",
        "영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수",
    ]

    # 표 출력 (숫자 세파레이터 포맷팅 적용)
    st.dataframe(
        display_df.style.format(
            {
                "순위": "{:,}위",
                "관객수": "{:,}명",
                "누적관객": "{:,}명",
                "스크린수": "{:,}개",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
