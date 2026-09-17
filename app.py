import datetime
import joblib
import pandas as pd
import requests
import streamlit as st

# 1. Streamlit 기본 페이지 설정
st.set_page_config(
    page_title="AI 자습실 혼잡도 예측 시스템", page_icon="🏫", layout="wide"
)

st.markdown(
    """
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 20px; }
    </style>
""",
    unsafe_allow_html=True,
)

# 서브 타이틀 문구를 제거하고 메인 타이틀만 깔끔하게 남겼습니다.
st.markdown(
    '<p class="main-title">🏫 AI 자습실 혼잡도 예측 대시보드</p>',
    unsafe_allow_html=True,
)

CAPACITY = 66  # 학년별 자습실 정원 (총 210명)
API_KEY = st.secrets["OPENWEATHER_API_KEY"]
CITY_NAME = "Seoul"


# 2. 날씨 API 조회 함수
def get_weather_forecast(api_key, target_date, city="Seoul"):
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        if response.status_code == 200:
            target_str = target_date.strftime("%Y-%m-%d")
            day_forecasts = [
                item
                for item in data.get("list", [])
                if item.get("dt_txt", "").startswith(target_str)
            ]
            if day_forecasts:
                has_rain = any(
                    any(
                        w in w_info.get("main", "").lower()
                        for w in ["rain", "snow", "drizzle", "thunderstorm"]
                    )
                    for item in day_forecasts
                    for w_info in item.get("weather", [])
                )
                if has_rain:
                    return 1, f"🌧️ [{city}] {target_str} 강수 예보 감지됨"
                else:
                    return 0, f"☀️ [{city}] {target_str} 맑음/구름 예보"
            else:
                return (
                    0,
                    f"ℹ️ [{city}] 5일 예보 범위를 벗어난 날짜 (기본 맑음)",
                )
        else:
            return 0, f"⚠️ 날씨 API 오류 발생"
    except Exception:
        return 0, f"⚠️ 네트워크 연결 실패"


# 3. 혼잡도 상태 반환 함수
def get_status(rate):
    if rate >= 80:
        return "🔴 매우 혼잡"
    elif rate >= 50:
        return "🟡 보통"
    else:
        return "🟢 여유"


# 4. 사이드바 조건 선택 영역
st.sidebar.header("⚙️ 예측 조건 설정")
selected_date = st.sidebar.date_input("📅 조회할 날짜", datetime.date.today())
day_of_week = selected_date.weekday()  # 월=0 ~ 일=6

# --- [학사 일정 및 방학 정의] ---
vacation_start = datetime.date(2026, 7, 22)
vacation_end = datetime.date(2026, 8, 17)
is_vacation = vacation_start <= selected_date <= vacation_end

exam_periods = [
    (datetime.date(2026, 4, 24), datetime.date(2026, 4, 24)),
    (datetime.date(2026, 4, 27), datetime.date(2026, 4, 30)),
    (datetime.date(2026, 6, 29), datetime.date(2026, 7, 3)),
    (datetime.date(2026, 10, 1), datetime.date(2026, 10, 2)),
    (datetime.date(2026, 10, 6), datetime.date(2026, 10, 8)),
    (datetime.date(2026, 12, 8), datetime.date(2026, 12, 11)),
    (datetime.date(2026, 12, 14), datetime.date(2026, 12, 14)),
]

is_exam = 0
for start, end in exam_periods:
    if start <= selected_date <= end:
        is_exam = 1
        break

future_exams = [start for start, end in exam_periods if selected_date < start]
if is_exam == 1:
    event_str = "💯 시험 기간"
    exam_dday = 0
elif future_exams:
    next_exam = min(future_exams)
    exam_dday = (next_exam - selected_date).days
    event_str = f"✍️ 다가오는 시험 D-{exam_dday}"
elif is_vacation:
    event_str = "🏖️ 여름방학 기간"
    exam_dday = 99
else:
    event_str = "📘 정규 수업일"
    exam_dday = 99

# --- [운영 시간 및 세션 설정] ---
if day_of_week == 6:  # 일요일
    st.sidebar.warning("🚫 일요일은 자습실 휴무일입니다.")
    time_slot = 0
elif day_of_week == 5:  # 토요일
    time_slot = st.sidebar.selectbox(
        "⏰ 시간대 선택 (토요일)",
        options=[1, 2],
        format_func=lambda x: (
            "1차 세션 (09:00~13:00)" if x == 1 else "2차 세션 (13:00~17:00)"
        ),
    )
else:  # 평일
    if is_vacation:
        time_slot = st.sidebar.selectbox(
            "⏰ 시간대 선택 (방학 평일)",
            options=[1, 2, 3],
            format_func=lambda x: {
                1: "1차 세션 (09:00~12:00)",
                2: "2차 세션 (12:00~14:30)",
                3: "3차 세션 (14:30~17:00)",
            }[x],
        )
    else:
        time_slot = st.sidebar.selectbox(
            "⏰ 시간대 선택 (학기 중 평일)",
            options=[1, 2, 3],
            format_func=lambda x: {
                1: "1차 세션 (13:00~15:00)",
                2: "2차 세션 (15:00~17:30)",
                3: "3차 세션 (17:30~20:00)",
            }[x],
        )

# 날씨 불러오기
is_raining, weather_msg = get_weather_forecast(
    API_KEY, selected_date, city=CITY_NAME
)
st.sidebar.info(weather_msg)

st.sidebar.markdown("---")
# 로켓 이모지를 제거한 버튼
predict_btn = st.sidebar.button(
    "혼잡도 예측 시작하기", type="primary", use_container_width=True
)

# 5. 메인 화면 구성
if day_of_week == 6:
    st.info("🚫 **일요일은 자습실이 운영되지 않습니다.** 휴일 푹 쉬세요!")
elif not predict_btn:
    st.info(
        "👈 왼쪽 사이드바에서 날짜와 운영 조건을 확인한 뒤 **[혼잡도 예측 시작하기]** 버튼을 눌러주세요!"
    )
else:
    st.markdown(f"### 📊 예측 결과 리포트")
    st.markdown(
        f"**조회 일자**: `{selected_date}` | **세션**: `{time_slot}차` | **상태**: `{event_str}`"
    )

    try:
        model = joblib.load("study_room_model.pkl")
        input_data = pd.DataFrame(
            [[day_of_week, time_slot, exam_dday, is_exam, is_raining]],
            columns=[
                "day_of_week",
                "time_slot",
                "exam_dday",
                "is_exam",
                "is_raining",
            ],
        )

        pred = model.predict(input_data)[0]
        g1_pred = max(0, int(round(pred[0])))
        g2_pred = max(0, int(round(pred[1])))
        g3_pred = max(0, int(round(pred[2])))
        total_pred = max(0, int(round(pred[3])))

    except Exception:
        st.error(
            "⚠️ AI 모델 파일을 찾지 못했습니다. 터미널에서 `python train_model.py`를 먼저 실행해 주세요."
        )
        g1_pred, g2_pred, g3_pred, total_pred = 0, 0, 0, 0

    g1_rate = min(100, round((g1_pred / CAPACITY) * 100))
    g2_rate = min(100, round((g2_pred / CAPACITY) * 100))
    g3_rate = min(100, round((g3_pred / CAPACITY) * 100))

    with st.container(border=True):
        st.markdown("#### 🏫 학년별 예상 인원 및 혼잡도")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "1학년 자습실",
            f"{g1_pred}명",
            f"{g1_rate}% ({get_status(g1_rate)})",
        )
        c2.metric(
            "2학년 자습실",
            f"{g2_pred}명",
            f"{g2_rate}% ({get_status(g2_rate)})",
        )
        c3.metric(
            "3학년 자습실",
            f"{g3_pred}명",
            f"{g3_rate}% ({get_status(g3_rate)})",
        )
        c4.metric("전체 인원 합계", f"{total_pred}명", "Total")

    st.markdown("#### 📈 학년별 혼잡도 비교 차트")
    chart_df = pd.DataFrame(
        {
            "학년": ["1학년", "2학년", "3학년"],
            "혼잡도(%)": [g1_rate, g2_rate, g3_rate],
        }
    )
    st.bar_chart(chart_df.set_index("학년"), color="#2563EB")