import datetime
import requests
import pandas as pd
import pytz
import streamlit as st
import altair as alt

# 페이지 기본 설정
st.set_page_config(
    page_title="일별 박스오피스 검색",
    page_icon="🎬",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. API 데이터 요청 함수 (캐싱 적용)
# @st.cache_data를 이용해 동일 날짜 요청은 1시간 동안 기억합니다.
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
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


# -----------------------------------------------------------------------------
# 2. 메인 화면 및 인증키(Secrets) 확인
# -----------------------------------------------------------------------------
st.title("🎬 일별 박스오피스 조회")

# Secrets에서 KOBIS_KEY 가져오기
api_key = st.secrets.get("KOBIS_KEY")

if not api_key:
    st.error("🔑 API 키를 찾을 수 없습니다.")
    st.warning("Streamlit Cloud 대시보드의 App Settings > Secrets에 KOBIS_KEY를 설정해 주세요.")
    st.stop()


# -----------------------------------------------------------------------------
# 3. 날짜 선택 (한국 시간 KST 기준어제까지 선택 가능)
# -----------------------------------------------------------------------------
tz_kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(tz_kst)
yesterday = (now_kst - datetime.timedelta(days=1)).date()

# 달력 위젯 생성 (최대 선택 가능한 날짜는 어제까지)
selected_date = st.date_input(
    label="📅 조회할 날짜를 선택하세요 (최대 어제까지 선택 가능)",
    value=yesterday,
    max_value=yesterday
)

# 선택된 날짜를 API 요청용 형식(YYYYMMDD) 및 표시용 형식으로 변환
target_date_str = selected_date.strftime("%Y%m%d")
display_date_str = selected_date.strftime("%Y년 %m월 %d일")

st.caption(f"조회 기준일: **{display_date_str}**")


# -----------------------------------------------------------------------------
# 4. 데이터 로딩 및 검증
# -----------------------------------------------------------------------------
with st.spinner("박스오피스 데이터를 불러오는 중입니다..."):
    data = fetch_box_office_data(target_date_str, api_key)

# 1) 네트워크 요청 실패인 경우
if data is None:
    st.error("🚨 API 서버 연결에 실패했습니다.")
    st.info("네트워크 상태를 확인하시거나 잠시 후 다시 시도해 주세요.")
    st.stop()

# 2) 인증키 오류 등으로 faultInfo 상자가 온 경우
if "faultInfo" in data:
    fault_msg = data["faultInfo"].get("message", "알 수 없는 오류")
    st.error(f"🚨 API 요청 오류 발생: {fault_msg}")
    st.info("Streamlit Secrets에 등록한 KOBIS_KEY가 정확한지 확인해 주세요.")
    st.stop()

# 3) 영화 목록 추출
box_office_result = data.get("boxOfficeResult", {})
movie_list = box_office_result.get("dailyBoxOfficeList", [])

# 4) 영화 목록이 비어있는 경우 (요청사항 반영)
if not movie_list:
    st.info("그날은 아직 집계 전입니다.")
    st.stop()


# -----------------------------------------------------------------------------
# 5. 데이터 전처리 (숫자 변환, 트로피 부착, 순위 증감 화살표 적용)
# -----------------------------------------------------------------------------
df = pd.DataFrame(movie_list)

# 문자열 숫자를 정수형으로 변환
numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    else:
        df[col] = 0

# 기본 순위 정렬
df = df.sort_values(by="rank", ascending=True)

# 1) 누적관객 100만 명 이상 영화명 옆에 트로피(🏆) 이모지 추가
def format_movie_title(row):
    title = str(row["movieNm"])
    if row["audiAcc"] >= 1000000:
        return f"{title} 🏆"
    return title

df["display_movieNm"] = df.apply(format_movie_title, axis=1)

# 2) 순위 증감(rankInten) 화살표 텍스트 생성 (양수: 🔺, 음수: 🔹)
def format_rank_change(val):
    if val > 0:
        return f"🔺 {val}"
    elif val < 0:
        return f"🔹 {abs(val)}"
    else:
        return "-"

df["rank_change_str"] = df["rankInten"].apply(format_rank_change)


# -----------------------------------------------------------------------------
# 6. 화면 출력 (1위 지표 카드 / Top 5 막대그래프 / 전체 표)
# -----------------------------------------------------------------------------

# [1위 영화 지표 카드 세 장]
st.markdown("### 🏆 해당 일자 1위 영화")
top_1 = df.iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric(
    label="🎬 영화명",
    value=str(top_1["display_movieNm"]),
    delta=f"개봉일: {top_1.get('openDt', '-')}"
)
col2.metric(
    label="🍿 당일 관객 수",
    value=f"{int(top_1['audiCnt']):,} 명"
)
col3.metric(
    label="👥 누적 관객 수",
    value=f"{int(top_1['audiAcc']):,} 명"
)

st.divider()

# [관객 수 기준 Top 5 막대그래프]
st.markdown("### 📊 관객 수 Top 5 영화")

# 관객 수(audiCnt) 내림차순 상위 5개 추출
top_5_df = df.sort_values(by="audiCnt", ascending=False).head(5)

chart = (
    alt.Chart(top_5_df)
    .mark_bar()
    .encode(
        x=alt.X("movieNm:N", sort="-y", title="영화명"),
        y=alt.Y("audiCnt:Q", title="당일 관객 수 (명)"),
        tooltip=["movieNm", "audiCnt"]
    )
    .properties(height=350)
)

st.altair_chart(chart, use_container_width=True)

st.divider()

# [전체 Top 10 순위표]
st.markdown("### 📋 전체 순위표 (Top 10)")

# 표로 나타낼 항목 정리
display_df = df[["rank", "rank_change_str", "display_movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
display_df.columns = ["순위", "순위 증감", "영화명", "개봉일", "당일 관객수", "누적 관객수", "스크린수"]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(format="%d 위"),
        "당일 관객수": st.column_config.NumberColumn(format="%d 명"),
        "누적 관객수": st.column_config.NumberColumn(format="%d 명"),
        "스크린수": st.column_config.NumberColumn(format="%d 개")
    }
)
