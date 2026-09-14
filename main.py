import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="영화 데이터 그래프 도감 1 - 시간",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 영화 데이터 그래프 도감 1 - 시간")
st.markdown("---")


# 데이터 불러오기 및 전처리
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"
    df = pd.read_csv(url)

    # 날짜 열을 datetime 형식으로 변환 (YYYYMMDD -> YYYY-MM-DD)
    df["날짜"] = pd.to_datetime(df["날짜"].astype(str), format="%Y%m%d")

    return df


df = load_data()

# -------------------------------------------------------------------
# 구역 1: 영화별 일별 관객수 변화 (선 그래프 + 주말 표시)
# -------------------------------------------------------------------
st.header("1. 개별 영화 일관객수 추이")

# 영화 목록 추출 (오름차순 정렬)
movie_list = sorted(df["영화명"].dropna().unique())

# 영화 선택 드롭다운
selected_movie = st.selectbox(
    "관객수 변화를 확인할 영화를 선택하세요:", movie_list
)

# 선택한 영화 데이터 필터링
movie_df = df[df["영화명"] == selected_movie].sort_values("날짜")

if not movie_df.empty:
    # Plotly 선 그래프 생성
    fig1 = px.line(
        movie_df,
        x="날짜",
        y="일관객",
        title=f"<{selected_movie}> 일별 관객수 변화 (음영 구간: 주말)",
        labels={"날짜": "날짜", "일관객": "일일 관객수 (명)"},
        markers=True,
    )

    # 주말(토요일, 일요일) 구간 찾아서 배경 음영 추가
    movie_dates = pd.date_range(start=movie_df["날짜"].min(), end=movie_df["날짜"].max(), freq="D")
    
    for single_date in movie_dates:
        if single_date.weekday() == 5:  # 토요일인 경우
            fig1.add_vrect(
                x0=single_date - pd.Timedelta(days=0.5),
                x1=single_date + pd.Timedelta(days=1.5),
                fillcolor="gray",
                opacity=0.15,
                line_width=0,
                layer="below",
            )

    # 마우스 오버(툴팁) 레이아웃 설정
    fig1.update_traces(
        hovertemplate="<b>날짜</b>: %{x|%Y-%m-%d}<br><b>일관객수</b>: %{y:,}명<extra></extra>"
    )
    fig1.update_layout(hovermode="x unified")

    st.plotly_chart(fig1, use_container_width=True)

    # 1번 구역 해석 문구
    st.info(
        "💡 **이 그래프로 알 수 있는 것:** 평일 주말에 따른 그래프 모양변화, 그래프 추세를 알수있다."
    )
else:
    st.warning("선택한 영화의 데이터가 없습니다.")

st.markdown("---")

# -------------------------------------------------------------------
# 구역 2: 누적 관객 상위 5개 영화 비교 (주말 음영 표시)
# -------------------------------------------------------------------
st.header("2. 기간 내 관객수 TOP 5 영화의 일일 관객수 비교 (주말 강조)")

# 전체 기간 내 총 일관객 합계 상위 5개 영화 추출
top5_movies = (
    df.groupby("영화명")["일관객"]
    .sum()
    .nlargest(5)
    .index.tolist()
)

# TOP 5 영화 데이터만 필터링
top5_df = df[df["영화명"].isin(top5_movies)].sort_values("날짜")

if not top5_df.empty:
    # Plotly 선 그래프 생성 (영화명별 색상 구분)
    fig2 = px.line(
        top5_df,
        x="날짜",
        y="일관객",
        color="영화명",
        title="기간 내 일관객수 합계 TOP 5 영화 추이 비교 (음영 구간: 주말)",
        labels={"날짜": "날짜", "일관객": "일일 관객수 (명)", "영화명": "영화 제목"},
        markers=False,
    )

    # 주말(토요일, 일요일) 구간 찾아서 배경 음영 추가
    unique_dates = pd.date_range(start=df["날짜"].min(), end=df["날짜"].max(), freq="D")
    
    for single_date in unique_dates:
        if single_date.weekday() == 5:  # 토요일인 경우
            fig2.add_vrect(
                x0=single_date - pd.Timedelta(days=0.5),
                x1=single_date + pd.Timedelta(days=1.5),
                fillcolor="gray",
                opacity=0.15,
                line_width=0,
                layer="below",
            )

    fig2.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>날짜: %{x|%Y-%m-%d}<br>일관객: %{y:,}명<extra></extra>"
    )
    fig2.update_layout(
        hovermode="x unified",
        legend_title_text="영화 (클릭하여 켜기/끄기)",
    )

    st.plotly_chart(fig2, use_container_width=True)

    # 2번 구역 해석 문구
    st.info(
        "💡 **이 그래프로 알 수 있는 것:** 공통적으로 주말에 관람객이 증가하는 추세를 알수있다."
    )

st.markdown("---")

# -------------------------------------------------------------------
# 구역 3: 날짜별 TOP 10 일관객 합계 (영역 그래프 + Peak 3일 표시)
# -------------------------------------------------------------------
st.header("3. 일일 전체 박스오피스(TOP 10) 총 관객수 추이")

# 날짜별 10위권 관객수 합계 계산
daily_total_df = (
    df.groupby("날짜")["일관객"]
    .sum()
    .reset_index()
    .sort_values("날짜")
)

# 합계 관객수가 가장 컸던 상위 3일 추출
top3_days = daily_total_df.nlargest(3, "일관객").reset_index(drop=True)

if not daily_total_df.empty:
    # 영역 그래프(Area Chart) 생성
    fig3 = px.area(
        daily_total_df,
        x="날짜",
        y="일관객",
        title="일별 TOP 10 전체 관객수 합계 추이 (최고 관객수 상위 3일 강조)",
        labels={"날짜": "날짜", "일관객": "TOP 10 총 관객수 (명)"},
    )

    # 상위 3개 피크 날짜에 주석(Annotation) 표시 추가
    for rank, row in top3_days.iterrows():
        date_str = row["날짜"].strftime("%Y-%m-%d")
        audience_count = row["일관객"]
        
        fig3.add_annotation(
            x=row["날짜"],
            y=audience_count,
            text=f"<b>#{rank+1}위 Peak</b><br>{date_str}<br>({audience_count:,}명)",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#FF5722",
            ax=0,
            ay=-50,
            bgcolor="#FFF3E0",
            bordercolor="#FF5722",
            borderwidth=1,
            borderpad=4,
            font=dict(size=11, color="#D84315"),
        )

    fig3.update_traces(
        hovertemplate="<b>날짜</b>: %{x|%Y-%m-%d}<br><b>TOP 10 총 관객수</b>: %{y:,}명<extra></extra>",
        fillcolor="rgba(31, 119, 180, 0.3)",
        line_color="#1f77b4"
    )
    fig3.update_layout(hovermode="x unified")

    st.plotly_chart(fig3, use_container_width=True)

    st.info(
        f"💡 **이 그래프로 알 수 있는 것:** 1년 중 전체 극장가 관객 총합이 가장 많았던 날은 **1위 {top3_days.iloc[0]['날짜'].strftime('%Y-%m-%d')} ({top3_days.iloc[0]['일관객']:,}명)**이며, 명절/연휴나 대작 개봉 시즌 등 극장 전체 시장 규모의 성수기와 비수기 흐름을 한눈에 파악할 수 있습니다."
    )

st.markdown("---")

# -------------------------------------------------------------------
# 구역 4: 기간 내 총 관객수 TOP 10 영화 순위 (가로 막대그래프)
# -------------------------------------------------------------------
st.header("4. 기간 내 총 관객수 TOP 10 영화 순위 및 차트인 일수")

# 영화별 총 관객수 및 10위권 진입 일수 집계
movie_summary = (
    df.groupby("영화명")
    .agg(
        총관객수=("일관객", "sum"),
        진입일수=("날짜", "nunique")
    )
    .reset_index()
)

# 총 관객수 기준 TOP 10 추출
top10_summary = movie_summary.nlargest(10, "총관객수")

if not top10_summary.empty:
    # 가로 막대그래프 생성
    fig4 = px.bar(
        top10_summary,
        x="총관객수",
        y="영화명",
        orientation="h",
        title="기간 내 총 관객수 TOP 10 영화 (마우스 오버 시 10위권 유지 일수 표시)",
        labels={"총관객수": "총 관객수 (명)", "영화명": "영화 제목", "진입일수": "10위권 진입 일수"},
        color="총관객수",
        color_continuous_scale="Viridis",
        hover_data={"진입일수": True, "총관객수": ":,"},
    )

    fig4.update_layout(
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
    )

    fig4.update_traces(
        hovertemplate="<b>%{y}</b><br>총 관객수: %{x:,}명<br>10위권 진입 일수: %{customdata[0]}일<extra></extra>"
    )

    st.plotly_chart(fig4, use_container_width=True)

    longest_movie = top10_summary.nlargest(1, "진입일수").iloc[0]

    st.info(
        f"💡 **이 그래프로 알 수 있는 것:** 해당 기간 최고 흥행작의 순위를 직관적으로 알 수 있으며, 관객수 TOP 10 중 **'{longest_movie['영화명']}'**(이)가 **{longest_movie['진입일수']}일** 동안 10위권을 유지하며 가장 장기 흥행을 기록했음을 확인할 수 있습니다."
    )

st.markdown("---")

# -------------------------------------------------------------------
# 구역 5: 월×요일별 일관객 합계 히트맵
# -------------------------------------------------------------------
st.header("5. 월×요일별 관객수 집계 (히트맵)")

# 월, 요일 추출 및 요일 순서 정렬
df_heatmap = df.copy()
df_heatmap["월"] = df_heatmap["날짜"].dt.month.astype(str) + "월"

# 요일명 추출 및 월요일~일요일 순서 정의
days_order = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
day_mapping = {
    0: "월요일",
    1: "화요일",
    2: "수요일",
    3: "목요일",
    4: "금요일",
    5: "토요일",
    6: "일요일",
}
df_heatmap["요일"] = df_heatmap["날짜"].dt.weekday.map(day_mapping)

# 피벗 테이블 생성 (월 x 요일별 관객수 합계)
pivot_df = df_heatmap.pivot_table(
    index="월", columns="요일", values="일관객", aggfunc="sum"
)

# 월 순서 (1월~12월) 및 요일 순서 (월~일) 재정렬
month_order = [f"{m}월" for m in range(1, 13) if f"{m}월" in pivot_df.index]
pivot_df = pivot_df.reindex(index=month_order, columns=days_order)

if not pivot_df.empty:
    # Plotly 히트맵 생성 (색상이 진할수록 관객수 많음: Blues 스케일)
    fig5 = px.imshow(
        pivot_df,
        labels=dict(x="요일", y="월", color="총 관객수 (명)"),
        x=days_order,
        y=month_order,
        color_continuous_scale="Blues",
        title="월×요일별 일관객 합계 히트맵",
        text_auto=",d",  # 관객수 천 단위 콤마 자동 서식
    )

    fig5.update_layout(
        xaxis_title="요일",
        yaxis_title="월",
        coloraxis_colorbar=dict(title="총 관객수"),
    )

    fig5.update_traces(
        hovertemplate="<b>%{y} %{x}</b><br>총 관객수: %{z:,}명<extra></extra>"
    )

    st.plotly_chart(fig5, use_container_width=True)

    st.info(
        "💡 **이 그래프로 알 수 있는 것:** 각 월별로 어떤 요일에 관객이 집중되는지, 연중 극장 성수기(여름·겨울 방학 및 연휴 시즌)와 특정 요일(주말)의 시너지 효과를 직관적으로 파악할 수 있습니다."
    )
