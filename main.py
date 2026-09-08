import datetime
import requests
import pandas as pd
import pytz
import streamlit as st
import altair as alt

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
