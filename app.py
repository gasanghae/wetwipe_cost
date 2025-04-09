# Streamlit 기반 물티슈 원가계산 웹 앱
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import os
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# 전체 계산 함수 정의 포함
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'  # 한글 깨짐 방지용 기본 글꼴

def calculate_wetwipe_cost(width_mm, height_mm, gsm, exchange_rate, percent_applied, quantity_per_unit, margin_rate=0.10,
                             labor_cost=23.42, insurance_cost=4.17, management_cost=21.26, interest_cost=17.01, storage_cost=5.00, logistics_cost=28.57):
    area_m2 = (width_mm / 1000) * (height_mm / 1000)
    usd_price_per_kg = 1.46
    applied_usd_price = usd_price_per_kg * percent_applied
    unit_price_per_g = applied_usd_price * exchange_rate / 1000
    gsm_price = unit_price_per_g * gsm
    loss_rate_fabric = 0.05
    applied_unit_price = gsm_price * (1 + loss_rate_fabric)
    fabric_cost_per_sheet = area_m2 * applied_unit_price
    fabric_cost_total = fabric_cost_per_sheet * quantity_per_unit

    fabric_unit_price_per_sheet = round(fabric_cost_per_sheet, 4)
    fabric_unit_cost = round(fabric_cost_total, 2)

    submaterials = {
        "정제수": 1.20,
        "명진 메인": 15.41,
        "명진 소듐": 7.40,
        "명진 인산": 1.39,
        "SPC팩(파우치)": 56.24,
        "영신피엔엘(캡스티커)": 19.16,
        "나우텍(캡)": 33.33,
        "영신피엔엘(이너스티커)": 18.54,
        "지피엠(박스)": 77.77
    }

    processing_costs = {
        "물류비": logistics_cost,
        "노무비": labor_cost,
        "4대보험+퇴직금": insurance_cost,
        "제조경비": management_cost,
        "이자비용": interest_cost,
        "창고료": storage_cost
    }

    materials_total = fabric_cost_total + sum(submaterials.values())
    processing_total = sum(processing_costs.values())
    total_cost = materials_total + processing_total

    margin = total_cost * margin_rate
    final_price = round(total_cost + margin, -1)

    cost_summary = {
        "Sateri(원단) 총합": fabric_unit_cost,
        **submaterials,
        "-- 원부자재 소계": round(materials_total, 2),
        **processing_costs,
        "-- 임가공비 소계": round(processing_total, 2),
        "총원가": round(total_cost, 2),
        "마진({}%)".format(int(margin_rate * 100)): round(margin, 2),
        "제안가(판매가)": final_price
    }

    return cost_summary, fabric_unit_price_per_sheet, submaterials, processing_costs, final_price

# 결과 조회 페이지 + 복원/이름/태그 기능
if st.sidebar.button("📂 지난 견적 불러오기"):
    st.subheader("📋 저장된 견적 목록 및 복원")
    if os.path.exists("견적_기록.csv"):
        df_log = pd.read_csv("견적_기록.csv")
        if '견적명' not in df_log.columns:
            df_log['견적명'] = ''
        if '태그' not in df_log.columns:
            df_log['태그'] = ''
        st.dataframe(df_log)
        selected_row = st.selectbox("📌 복원할 견적 선택 (번호)", df_log.index)
        if st.button("📤 이 견적으로 계산기 채우기"):
            st.session_state.restore_data = df_log.loc[selected_row].to_dict()
            st.experimental_rerun()

        # 검색 옵션
        search_col = st.selectbox("🔍 검색할 항목", df_log.columns.tolist(), index=0)
        keyword = st.text_input("검색어 입력")
        if keyword:
            filtered = df_log[df_log[search_col].astype(str).str.contains(keyword, case=False)]
            st.dataframe(filtered)

            if not filtered.empty:
                selected_filtered = st.selectbox("📌 복원할 견적 선택 (번호)", filtered.index)
                if st.button("📤 검색 결과 견적으로 계산기 채우기"):
                    st.session_state.restore_data = filtered.loc[selected_filtered].to_dict()
                    st.experimental_rerun()
                st.success("🔎 검색 결과를 확인하세요.")
    else:
        st.info("아직 저장된 견적이 없습니다. 계산 후 저장됩니다.")

# 복원 기능 처리
if 'restore_data' in st.session_state:
    restore = st.session_state.restore_data
    st.toast("🔁 이전 견적 데이터를 계산기에 복원합니다")
    width = int(restore.get("규격", "150x195").split("x")[0])
    height = int(restore.get("규격", "150x195").split("x")[1])
    gsm = int(restore.get("평량", 40))
    quantity = int(restore.get("매수", 100))
    exchange_rate = float(restore.get("환율", 1500))
    percent_applied = float(restore.get("관세비율", 1.2))
    margin_rate = float(restore.get("마진율", 0.1))
