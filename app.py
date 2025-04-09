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



# 메인 입력 UI (계산기 입력 폼)
with st.form("calc_form"):
    st.subheader("📥 기본 입력값")
    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input("가로 길이 (mm)", value=150)
        gsm = st.number_input("평량 (g/㎡)", value=40)
        exchange_rate = st.number_input("환율 (₩/$)", value=1500)
        quantity = st.number_input("매수 (장 수)", value=120)
    with col2:
        height = st.number_input("세로 길이 (mm)", value=195)
        percent_applied = st.number_input("관세 포함 비율 (%)", value=120) / 100
        margin_rate = st.slider("마진율 (%)", 0, 50, 10) / 100

    st.subheader("⚙️ 임가공비 입력")
    labor_cost = st.number_input("노무비", value=23.42)
    insurance_cost = st.number_input("4대보험+퇴직금", value=4.17)
    management_cost = st.number_input("제조경비", value=21.26)
    interest_cost = st.number_input("이자비용", value=17.01)
    storage_cost = st.number_input("창고료", value=5.00)
    logistics_cost = st.number_input("물류비", value=28.57)

    submitted = st.form_submit_button("계산하기")

if submitted:
    result, unit_price, submaterials, processing_costs, final_price = calculate_wetwipe_cost(
        width, height, gsm, exchange_rate, percent_applied, quantity,
        margin_rate=margin_rate,
        labor_cost=labor_cost,
        insurance_cost=insurance_cost,
        management_cost=management_cost,
        interest_cost=interest_cost,
        storage_cost=storage_cost,
        logistics_cost=logistics_cost
    )

    st.subheader("💡 계산 결과")
    st.write(f"🧮 **원단 단가 (1장당, 로스 적용가)**: {unit_price} 원")
    for k, v in result.items():
        st.write(f"**{k}**: {v} 원")

    # CSV 저장
    csv_file = "견적_기록.csv"
    row = [f"{width}x{height}", gsm, quantity, exchange_rate, percent_applied, margin_rate, result["총원가"], result["제안가(판매가)"]]
    if not os.path.exists(csv_file):
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["규격", "평량", "매수", "환율", "관세비율", "마진율", "총원가", "제안가"])
            writer.writerow(row)
    else:
        with open(csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    # PDF 저장
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(50, 800, "📄 물티슈 원가계산 결과")
    y = 780
    for k, v in result.items():
        c.drawString(50, y, f"{k}: {v} 원")
        y -= 18
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = 800
    c.save()
    st.download_button("📄 PDF로 다운로드", data=pdf_buffer.getvalue(), file_name="wetwipe_cost.pdf")

    # 엑셀 다운로드
    df_result = pd.DataFrame(result.items(), columns=["항목", "금액 (원)"])
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        df_result.to_excel(writer, index=False, sheet_name="견적서")
    st.download_button("📥 Excel로 다운로드", data=excel_buffer.getvalue(), file_name="wetwipe_cost.xlsx")

    # 시각화
    st.subheader("📊 원가 구성 시각화")
    group_labels = ['원단', '원부자재', '임가공비']
    group_values = [result['Sateri(원단) 총합'], sum(submaterials.values()), sum(processing_costs.values())]

    fig1, ax1 = plt.subplots()
    ax1.pie(group_values, labels=group_labels, autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')
    st.pyplot(fig1)

    st.subheader("📊 항목별 바 차트")
    bar_data = {
        "항목": list(submaterials.keys()) + list(processing_costs.keys()),
        "비용": list(submaterials.values()) + list(processing_costs.values())
    }
    df_bar = pd.DataFrame(bar_data)
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.barh(df_bar["항목"], df_bar["비용"], color="skyblue")
    ax2.set_xlabel("비용 (원)")
    st.pyplot(fig2)
