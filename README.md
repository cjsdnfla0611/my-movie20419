import datetime
import requests
import pandas as pd
import pytz
import streamlit as st

# 페이지 기본 설정 (타이틀, 레이아웃)
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. API 데이터 요청 함수 (캐싱 적용)
# Streamlit의 @st.cache_data를 이용해 1시간(3600초) 동안 동일 요청 결과를 저장합니다.
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_box_office_data(target_date: str, api_key: str):
    """
    KOBIS API를 호출하여 해당 날짜의 일별 박스오피스 데이터를 가져오는 함수입니다.
    """
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": api_key,
        "targetDt": target_date
    }
    
    try:
        # API 응답 요청 (타임아웃 10초 설정)
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
        return response.json()
    except requests.exceptions.RequestException as e:
        # 네트워크 에러 발생 시 None 반환
        return None

# -----------------------------------------------------------------------------
# 2. 메인 화면 구성
# -----------------------------------------------------------------------------
st.title("🎬 어제의 일별 박스오피스 Top 10")

# Streamlit Cloud의 비밀 금고(Secrets)에서 KOBIS_KEY 가져오기
api_key = st.secrets.get("KOBIS_KEY")

# API 키가 등록되어 있지 않은 경우 처리
if not api_key:
    st.error("🔑 API 키를 찾을 수 없습니다.")
    st.info(
        "Streamlit Cloud의 App Settings > Secrets에 아래와 같이 인증키를 추가해 주세요.\n\n"
        "```toml\n"
        'KOBIS_KEY = "발급받은_인증키_입력"\n'
        "```"
    )
    st.stop()

# 한국 시간(KST) 기준으로 '어제' 날짜 계산하기
# Streamlit Cloud 배포 서버 시계가 UTC(영국 표준시) 기준일 수 있으므로 시간대를 명시합니다.
tz_kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(tz_kst)
yesterday = now_kst - datetime.timedelta(days=1)
target_date_str = yesterday.strftime("%Y%m%d")  # YYYYMMDD 형태의 문자열로 변환
display_date_str = yesterday.strftime("%Y년 %m월 %d일")

st.caption(f"기준 일자: **{display_date_str}** (한국 시간 기준 어제)")

# 데이터 로딩 표시와 함께 API 호출
with st.spinner("박스오피스 데이터를 불러오는 중입니다..."):
    data = fetch_box_office_data(target_date_str, api_key)

# -----------------------------------------------------------------------------
# 3. 예외 및 오류 처리
# -----------------------------------------------------------------------------
# 1) 네트워크 요청 자체가 실패한 경우
if data is None:
    st.error("🚨 API 서버에 연결할 수 없습니다.")
    st.warning("네트워크 연결 상태를 확인하시거나 잠시 후 다시 시도해 주세요.")
    st.stop()

# 2) 인증키 오류 등으로 'faultInfo'가 반환된 경우
if "faultInfo" in data:
    fault_message = data["faultInfo"].get("message", "알 수 없는 오류")
    st.error(f"🚨 API 요청 오류가 발생했습니다: {fault_message}")
    st.info(
        "**확인해 주세요:**\n"
        "- Streamlit Secrets에 등록된 `KOBIS_KEY`가 올바른지 확인해 주세요.\n"
        "- 영화진흥위원회 통합전산망(KOBIS)에서 키가 정상 발급되었는지 확인해 주세요."
    )
    st.stop()

# 3) 응답 구조 내 영화 목록 추출
box_office_result = data.get("boxOfficeResult", {})
movie_list = box_office_result.get("dailyBoxOfficeList", [])

# 4) 영화 목록이 비어있는 경우
if not movie_list:
    st.warning("⚠️ 선택한 날짜의 박스오피스 데이터가 존재하지 않습니다.")
    st.info(
        "**확인해 주세요:**\n"
        "- 아직 어제 자 데이터 집계가 완료되지 않았을 수 있습니다.\n"
        "- KOBIS 점검 시간인지 확인해 주세요."
    )
    st.stop()

# -----------------------------------------------------------------------------
# 4. 데이터 전처리 (문자열 -> 숫자 변환)
# -----------------------------------------------------------------------------
df = pd.DataFrame(movie_list)

# 분석에 필요한 컬럼들을 정수(int) 타입으로 변환
numeric_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# 순위 기준으로 정렬
df = df.sort_values(by="rank", ascending=True)

# -----------------------------------------------------------------------------
# 5. 대시보드 화면 출력
# -----------------------------------------------------------------------------

# [1위 영화 지표 카드 (3장)]
st.markdown("### 🏆 어제 1위 영화")
top_1_movie = df.iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric(
    label="🎬 영화명",
    value=top_1_movie["movieNm"],
    delta=f"개봉일: {top_1_movie['openDt']}"
)
col2.metric(
    label="🍿 어제 관객 수",
    value=f"{top_1_movie['audiCnt']:,} 명"
)
col3.metric(
    label="👥 누적 관객 수",
    value=f"{top_1_movie['audiAcc']:,} 명"
)

st.divider()

# [관객 수 상위 5편 막대그래프]
st.markdown("### 📊 관객 수 상위 5개 영화")
top_5_df = df.head(5)

# Streamlit 내장 막대그래프 활용
st.bar_chart(
    data=top_5_df,
    x="movieNm",
    y="audiCnt",
    x_label="영화명",
    y_label="어제 관객 수 (명)"
)

st.divider()

# [전체 Top 10 데이터 표]
st.markdown("### 📋 전체 순위표 (Top 10)")

# 화면에 보여줄 컬럼 선택 및 이름 변경
display_df = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
display_df.columns = ["순위", "영화명", "개봉일", "어제 관객수", "누적 관객수", "스크린수"]

# 천 단위 쉼표(,) 포맷팅을 적용하여 표 출력
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
