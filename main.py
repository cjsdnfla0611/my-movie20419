import datetime
import requests
import pandas as pd
import pytz
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. API 데이터 요청 함수 (캐싱 적용)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_box_office_data(target_date: str, api_key: str):
    """
    KOBIS API를 호출하여 해당 날짜의 일별 박스오피스 데이터를 가져옵니다.
    """
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": api_key,
        "targetDt": target_date
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        # 네트워크 에러 등 발생 시 None 반환
        return None


# -----------------------------------------------------------------------------
# 2. 메인 화면 및 인증키 확인
# -----------------------------------------------------------------------------
st.title("🎬 어제의 일별 박스오피스 Top 10")

# Streamlit Secrets에서 API 키 읽어오기
api_key = None
if "KOBIS_KEY" in st.secrets:
    api_key = st.secrets["KOBIS_KEY"]

# API 키가 없거나 비어있는 경우 안내문 출력 후 중단
if not api_key:
    st.error("🔑 API 키를 찾을 수 없습니다.")
    st.info(
        "**Streamlit Cloud 설정 방법:**\n"
        "1. Streamlit Cloud 대시보드에서 해당 앱의 `Settings` > `Secrets`로 이동합니다.\n"
        "2. 아래와 같이 KOBIS_KEY를 설정해 주세요.\n\n"
        "```toml\n"
        'KOBIS_KEY = "발급받은_인증키_입력"\n'
        "```"
    )
    st.stop()


# -----------------------------------------------------------------------------
# 3. 날짜 계산 (한국 시간 KST 기준 '어제')
# -----------------------------------------------------------------------------
tz_kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(tz_kst)
yesterday = now_kst - datetime.timedelta(days=1)

target_date_str = yesterday.strftime("%Y%m%d")      # API 요청용 (YYYYMMDD)
display_date_str = yesterday.strftime("%Y년 %m월 %d일")  # 화면 표시용

st.caption(f"기준 일자: **{display_date_str}** (한국 시간 기준 어제)")


# -----------------------------------------------------------------------------
# 4. 데이터 로딩 및 검증
# -----------------------------------------------------------------------------
with st.spinner("박스오피스 데이터를 불러오는 중입니다..."):
    data = fetch_box_office_data(target_date_str, api_key)

# 1) 응답 결과 자체가 없는 경우
if data is None:
    st.error("🚨 API 서버 연결에 실패했습니다.")
    st.warning("네트워크 상태를 확인하시거나 잠시 후 다시 시도해 주세요.")
    st.stop()

# 2) KOBIS 에러 상자(faultInfo)가 포함되어 돌아온 경우 (인증키 오류 등)
if "faultInfo" in data:
    fault_info = data.get("faultInfo", {})
    message = fault_info.get("message", "알 수 없는 오류가 발생했습니다.")
    st.error(f"🚨 API 오류 발생: {message}")
    st.info(
        "**확인 사항:**\n"
        "- Streamlit Secrets에 입력한 `KOBIS_KEY` 값이 정확한지 확인해 주세요.\n"
        "- KOBIS 홈페이지에서 발급받은 키의 상태를 확인해 주세요."
    )
    st.stop()

# 3) 정상 결과에서 영화 목록 추출
box_office_result = data.get("boxOfficeResult", {})
movie_list = box_office_result.get("dailyBoxOfficeList", [])

# 4) 영화 목록이 비어있는 경우
if not movie_list:
    st.warning("⚠️ 해당 날짜의 박스오피스 데이터가 비어 있습니다.")
    st.info(
        "**확인 사항:**\n"
        "- 아직 어제 일자 집계가 완료되지 않았을 수 있습니다.\n"
        "- KOBIS 시스템 점검 시간인지 확인해 주세요."
    )
    st.stop()


# -----------------------------------------------------------------------------
# 5. 데이터 전처리 (문자열 -> 숫자 변환 및 정렬)
# -----------------------------------------------------------------------------
df = pd.DataFrame(movie_list)

# 숫자로 변환해야 하는 컬럼 리스트
target_cols = ["rank", "audiCnt", "audiAcc", "scrnCnt"]

for col in target_cols:
    if col in df.columns:
        # 문자열을 숫자로 안전하게 변환 (변환 불가한 값은 0 처리)
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    else:
        df[col] = 0

# 순위 기준 기본 정렬
df = df.sort_values(by="rank", ascending=True)


# -----------------------------------------------------------------------------
# 6. 화면 출력 (1위 지표 카드, 상위 5개 관객수 그래프, 전체 표)
# -----------------------------------------------------------------------------

# [1위 영화 지표 카드]
st.markdown("### 🏆 어제 1위 영화")
top_1 = df.iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric(
    label="🎬 영화명",
    value=str(top_1["movieNm"]),
    delta=f"개봉일: {top_1.get('openDt', '-')}"
)
col2.metric(
    label="🍿 어제 관객 수",
    value=f"{int(top_1['audiCnt']):,} 명"
)
col3.metric(
    label="👥 누적 관객 수",
    value=f"{int(top_1['audiAcc']):,} 명"
)

st.divider()

# [관객 수 기준 Top 5 막대그래프]
st.markdown("### 📊 관객 수 Top 5 영화")

# 어제 관객 수(audiCnt) 내림차순 정렬 후 상위 5개 추출
top_5_df = df.sort_values(by="audiCnt", ascending=False).head(5)

# Streamlit 내장 막대그래프 출력
st.bar_chart(
    data=top_5_df,
    x="movieNm",
    y="audiCnt",
    x_label="영화명",
    y_label="어제 관객 수 (명)"
)

st.divider()

# [전체 순위표]
st.markdown("### 📋 전체 순위표 (Top 10)")

display_df = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
display_df.columns = ["순위", "영화명", "개봉일", "어제 관객수", "누적 관객수", "스크린수"]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(format="%d 위"),
        "어제 관객수": st.column_config.NumberColumn(format="%d 명"),
        "누적 관객수": st.column_config.NumberColumn(format="%d 명"),
        "스크린수": st.column_config.NumberColumn(format="%d 개")
    }
)
