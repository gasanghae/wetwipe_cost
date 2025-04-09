# Streamlit 기반 물티슈 원가계산 웹 앱
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO

# PDF용 ReportLab은 옵션으로 제공 가능
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def calculate_wetwipe_cost(width_mm, height_mm, gsm, exchange_rate, percent_applied, quantity_per_unit, margin_rate=0.10,
                             labor_cost, insurance_cost, management_cost, interest_cost, storage_cost, logistics_cost):
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

st.set_page_config(page_title="물티슈 원가계산기", layout="centered")
st.title("📦 물티슈 원가계산기")

password = st.text_input("접속 비밀번호를 입력하세요", type="password")
if password != "1234":
    st.warning("올바른 비밀번호를 입력하세요.")
    st.stop()

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

    st.subheader("📁 계산 결과 다운로드")
    df_result = pd.DataFrame(result.items(), columns=["항목", "금액 (원)"])

    # Excel 저장
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_result.to_excel(writer, index=False, sheet_name="원가계산")
    st.download_button("📥 Excel로 다운로드", data=buffer.getvalue(), file_name="wetwipe_cost.xlsx")

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
    st.download_button("📄 PDF로 다운로드", data=pdf_buffer.getvalue(), file_name="wetwipe_cost.pdf"), file_name="wetwipe_cost.xlsx")
