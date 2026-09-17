import datetime
import os
import numpy as np
import pandas as pd

# data 폴더 생성
os.makedirs("data", exist_ok=True)

# 2026년 4월 날짜 생성
dates_apr = pd.date_range(start="2026-04-01", end="2026-04-30")
rows = []

# 중간고사 기간: 4월 24일, 27일~30일
exam_dates = [datetime.date(2026, 4, 24)] + list(
    pd.date_range("2026-04-27", "2026-04-30").date
)

for d in dates_apr:
  d_date = d.date()
  dow = d.weekday()
  if dow == 6:
    continue  # 일요일 휴무 제외

  is_exam = 1 if d_date in exam_dates else 0

  if is_exam:
    dday = 0
  elif d_date < datetime.date(2026, 4, 24):
    dday = (datetime.date(2026, 4, 24) - d_date).days
  else:
    dday = 99

  # 타임슬롯: 평일 3개, 토요일(5) 2개
  max_slot = 2 if dow == 5 else 3
  for slot in range(1, max_slot + 1):
    raining = np.random.choice([0, 1], p=[0.8, 0.2])
    base = 30 if not is_exam else 55
    if dday < 7 and not is_exam:
      base += 15

    # 70명 정원에 맞춘 자연스러운 인원 생성
    g1 = int(np.clip(np.random.normal(base, 8), 5, 70))
    g2 = int(np.clip(np.random.normal(base, 8), 5, 70))
    g3 = int(np.clip(np.random.normal(base + 5, 8), 5, 70))
    total = g1 + g2 + g3

    rows.append([
        d.strftime("%Y-%m-%d"),
        dow,
        slot,
        dday,
        is_exam,
        raining,
        g1,
        g2,
        g3,
        total,
    ])

# CSV로 저장 (UTF-8 인코딩)
df_apr = pd.DataFrame(
    rows,
    columns=[
        "date",
        "day_of_week",
        "time_slot",
        "exam_dday",
        "is_exam",
        "is_raining",
        "g1",
        "g2",
        "g3",
        "total",
    ],
)
df_apr.to_csv("data/2026_04.csv", index=False, encoding="utf-8-sig")

print("✨ 에러 없는 완벽한 4월 데이터(data/2026_04.csv)가 생성되었습니다!")
