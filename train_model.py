import glob
import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# 1. data 폴더 안의 CSV 파일 불러오기
file_list = glob.glob("data/*.csv")

if not file_list:
  print("⚠️ data 폴더에 CSV 파일이 없습니다!")
else:
  # 깔끔하게 표준 형식으로 읽기
  df_list = [pd.read_csv(f, encoding="utf-8-sig") for f in file_list]
  df = pd.concat(df_list, ignore_index=True)

  # 2. 학습용 입력 변수(X)와 정답(y) 설정 (70명 정원 기준)
  X = df[["day_of_week", "time_slot", "exam_dday", "is_exam", "is_raining"]]
  y = df[["g1", "g2", "g3", "total"]]

  # 3. Random Forest 모델 학습 및 저장
  model = RandomForestRegressor(n_estimators=100, random_state=42)
  model.fit(X, y)

  joblib.dump(model, "study_room_model.pkl")
  print(
      f"✅ 총 {len(df)}개 데이터로 AI 모델 학습 완료! (study_room_model.pkl"
      " 저장됨)"
  )