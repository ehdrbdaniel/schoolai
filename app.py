import datetime
import os
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

st.markdown(
    '<p class="main-title">🏫 AI 자습실 혼잡도 예측 대시보드</p>',
    unsafe_allow_html=True,
)

# 학년별 자습실 정원 (각 80명)
CAPACITY = 80

try:
  API_KEY = st.secrets["OPENWEATHER_API_KEY"]
except (FileNotFoundError, KeyError):
  API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
CITY_NAME = "Seoul"


# 2. 날씨 API 조회 함수
def get_weather_forecast(api_key, target_date, city="Seoul"):
  if not api_key:
    return 0, "⚠️ OPENWEATHER_API_KEY가 설정되지 않았습니다. 날씨 없이 예측합니다."

  try:
    response = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"q": city, "appid": api_key, "units": "metric"},
        timeout=3,
    )
    if response.status_code == 401:
      return 0, "⚠️ OpenWeather API 키가 유효하지 않거나 활성화되지 않았습니다."
    if response.status_code == 200:
      data = response.json()
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
        return 0, f"ℹ️ [{city}] 5일 예보 범위를 벗어난 날짜 (기본 맑음)"
    else:
      return 0, f"⚠️ 날씨 API 오류 발생 (HTTP {response.status_code})"
  except ValueError:
    return 0, "⚠️ 날씨 API 응답을 읽을 수 없습니다."
  except requests.RequestException:
    return 0, "⚠️ 네트워크 연결 실패"


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
            1: "1차 세션 (15:30~18:25)",
            2: "2차 세션 (18:30~20:25)",
            3: "3차 세션 (20:30~22:30)",
        }[x],
    )

# 날씨 불러오기
is_raining, weather_msg = get_weather_forecast(
    API_KEY, selected_date, city=CITY_NAME
)
st.sidebar.info(weather_msg)

st.sidebar.markdown("---")
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
    if not os.path.exists("study_room_model.pkl"):
      raise FileNotFoundError(
          "⚠️ 학습된 모델 파일(`study_room_model.pkl`)이 없습니다."
      )

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
    # 전체 인원은 학년별 예측값의 합으로 일관성 유지
    total_pred = g1_pred + g2_pred + g3_pred

  except FileNotFoundError as fnf_err:
    st.error(f"{fnf_err} 터미널에서 `python train_model.py`를 먼저 실행해 주세요.")
    st.stop()
  except Exception as e:
    st.error(f"⚠️ 예측 처리 중 오류가 발생했습니다: {e}")
    st.stop()

  # 학년별 정원 80명 기준 점유율 계산
  g1_rate = min(100, round((g1_pred / CAPACITY) * 100))
  g2_rate = min(100, round((g2_pred / CAPACITY) * 100))
  g3_rate = min(100, round((g3_pred / CAPACITY) * 100))

  # --- 화면 UI 출력 ---
  with st.container(border=True):
    st.markdown("#### 🏫 학년별 예상 인원 및 혼잡도 (정원 각 80명)")
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

  # 차트 가로폭을 줄이기 위해 컬럼으로 가운데 배치 ([1, 2, 1] 비율)
  left_col, center_col, right_col = st.columns([1, 2, 1])
  with center_col:
    st.bar_chart(chart_df.set_index("학년"), color="#2563EB")
