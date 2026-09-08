from datetime import datetime, timedelta
import zoneinfo
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="박스오피스 도감",
    page_icon="🎬",
    layout="wide",
)


# ==========================================
# 1. API 데이터 불러오기 함수 (캐싱 적용)
# ==========================================
# 날짜(target_date)별로 API 결과를 1시간(3600초) 동안 저장(캐싱)합니다.
@st.cache_data(ttl=3600)
def fetch_daily_boxoffice(target_date: str, api_key: str):
    """KOBIS API를 호출하여 선택한 날짜의 박스오피스 데이터를 가져옵니다."""
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": target_date}

    try:
        response = requests.get(url, params=params, timeout=10)

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
                "💡 **확인 사항:** Streamlit Secrets에 `KOBIS_KEY`가 올바르게 입력되었는지 확인해 주세요.",
            )

        # [에러 처리 2] 응답 구조 확인 및 영화 목록 존재 여부 검사
        boxoffice_result = data.get("boxOfficeResult", {})
        daily_list = boxoffice_result.get("dailyBoxOfficeList", [])

        # 영화 목록이 비어있는 경우
        if not daily_list:
            return None, "그날은 아직 집계 전입니다."

        return daily_list, None

    except requests.exceptions.RequestException as e:
        return (
            None,
            f"네트워크 통신 중 오류가 발생했습니다.\n상세 내용: {e}\n\n"
            "💡 **확인 사항:** 인터넷 연결 상태나 KOBIS 서버 상태를 확인해 주세요.",
        )


# ==========================================
# 2. 순위 변동 텍스트 생성 함수
# ==========================================
def format_rank_change(row):
    """rankInten 및 rankOldAndNew 값을 받아 상승/하강 기호 문자를 만듭니다."""
    is_new = row.get("rankOldAndNew") == "NEW"
    if is_new:
        return "NEW"

    try:
        inten = int(row.get("rankInten", 0))
    except (ValueError, TypeError):
        inten = 0

    if inten > 0:
        return f"🔺 {inten}"  # 상승 (빨간 위 화살표)
    elif inten < 0:
        return f"🔹 {abs(inten)}"  # 하강 (파란 아래 화살표)
    else:
        return "-"  # 변동 없음


# ==========================================
# 3. 메인 화면 및 데이터 처리
# ==========================================
def main():
    st.title("🎬 날짜별 박스오피스 도감")

    # [Secrets 확인] 비밀 금고에서 KOBIS_KEY 불러오기
    if "KOBIS_KEY" not in st.secrets:
        st.error(
            "🔑 **KOBIS_KEY가 설정되지 않았습니다.**\n\n"
            "Streamlit Cloud의 App Settings -> **Secrets** 메뉴에서 API 키를 입력해 주세요."
        )
        st.stop()

    api_key = st.secrets["KOBIS_KEY"]

    # [날짜 설정] 한국 시간(Asia/Seoul) 기준 '어제' 날짜 구하기
    korea_tz = zoneinfo.ZoneInfo("Asia/Seoul")
    today_korea = datetime.now(korea_tz).date()
    max_allowed_date = today_korea - timedelta(days=1)  # 선택 가능한 가장 늦은 날짜 (어제)

    # [달력 UI] 사용자로부터 날짜 선택 받기 (최대 날짜: 어제)
    selected_date = st.date_input(
        "📅 조회할 날짜를 선택하세요 (어제 날짜까지 조회 가능):",
        value=max_allowed_date,
        max_value=max_allowed_date,
    )

    # YYYYMMDD 여덟 자리 문자열 및 화면 표시용 문자열 생성
    target_date_str = selected_date.strftime("%Y%m%d")
    display_date_str = selected_date.strftime("%Y년 %m월 %d일")

    st.caption(f"기준 날짜: {display_date_str}")
    st.divider()

    # API 데이터 가져오기
    daily_list, error_message = fetch_daily_boxoffice(target_date_str, api_key)

    # 오류 또는 데이터 없음 안내 출력
    if error_message:
        st.warning(error_message)
        st.stop()

    # 데이터프레임(Dataframe) 변환
    df = pd.DataFrame(daily_list)

    # [숫자 형변환] 문자열 형태의 숫자를 정수형(int)으로 변환
    numeric_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt", "rankInten"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # 순위 기준 정렬
    df = df.sort_values("rank").reset_index(drop=True)

    # [순위 증감 문자열 생성]
    df["순위변동"] = df.apply(format_rank_change, axis=1)

    # [누적관객 100만 이상 트로피 🏆 표시]
    df["표시영화명"] = df.apply(
        lambda r: f"🏆 {r['movieNm']}" if r["audiAcc"] >= 1_000_000 else r["movieNm"],
        axis=1,
    )

    # ==========================================
    # 4. 1위 영화 지표 카드 (Metric Card)
    # ==========================================
    top_1 = df.iloc[0]

    st.subheader(f"🥇 {display_date_str} 1위 영화: {top_1['표시영화명']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="당일 관객 수",
            value=f"{top_1['audiCnt']:,} 명",
            delta=f"순위 변동: {top_1['순위변동']}",
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
    # 5. 관객수 상위 5편 막대그래프
    # ==========================================
    st.subheader("📊 관객수 상위 5개 영화")

    top5_df = df.head(5).copy()
    top5_df_sorted = top5_df.sort_values("audiCnt", ascending=True)

    fig = px.bar(
        top5_df_sorted,
        x="audiCnt",
        y="표시영화명",
        orientation="h",
        text="audiCnt",
        labels={"audiCnt": "일일 관객 수 (명)", "표시영화명": "영화명"},
        title=f"{display_date_str} 관객 수 Top 5",
        color="audiCnt",
        color_continuous_scale="Blues",
    )

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
    # 6. 전체 박스오피스 순위 표
    # ==========================================
    st.subheader("📋 전체 순위 (Top 10)")

    # 화면에 보여줄 열 선택 및 이름 변경
    display_df = df[
        ["rank", "순위변동", "표시영화명", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
    ].copy()

    display_df.columns = [
        "순위",
        "순위 변동",
        "영화명",
        "개봉일",
        "당일 관객수",
        "누적 관객수",
        "스크린수",
    ]

    # 표 출력
    st.dataframe(
        display_df.style.format(
            {
                "순위": "{:,}위",
                "당일 관객수": "{:,}명",
                "누적 관객수": "{:,}명",
                "스크린수": "{:,}개",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
