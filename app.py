
# Streamlit 기반 물티슈 원가계산 웹 앱
import streamlit as st

def calculate_wetwipe_cost(width_mm, height_mm, gsm, exchange_rate, tariff_rate, quantity_per_unit=120, margin_rate=0.10):
    area_m2 = (width_mm / 1000) * (height_mm / 1000)
    usd_price = 1.46  # 원단 기준 가격 (USD)
    unit_price_per_gsm = usd_price * exchange_rate * (1 + tariff_rate)
    loss_rate_fabric = 0.05
    applied_unit_price = unit_price_per_gsm * (1 + loss_rate_fabric)
    fabric_cost_per_sheet = area_m2 * gsm * applied_unit_price
    fabric_cost_total = fabric_cost_per_sheet * quantity_per_unit

    # 원부자재 항목들 (회사명 기반 항목 포함)
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

    # 임가공비용 항목들
    processing_costs = {
        "물류비": 28.57,
        "노무비": 23.42,
        "4대보험+퇴직금": 4.17,
        "제조경비": 21.26,
        "이자비용": 17.01,
        "창고료": 5.00  # 예시 값
    }

    materials_total = fabric_cost_total + sum(submaterials.values())
    processing_total = sum(processing_costs.values())
    total_cost = materials_total + processing_total

    margin = total_cost * margin_rate
    final_price = round(total_cost + margin, -1)

    cost_summary = {
        "Sateri(원단)": round(fabric_cost_total, 2),
        **submaterials,
        "-- 원부자재 소계": round(materials_total, 2),
        **processing_costs,
        "-- 임가공비 소계": round(processing_total, 2),
        "총원가": round(total_cost, 2),
        "마진({}%)".format(int(margin_rate * 100)): round(margin, 2),
        "제안가(판매가)": final_price
    }

    return cost_summary

# Streamlit UI
st.set_page_config(page_title="물티슈 원가계산기", layout="centered")
st.title("📦 물티슈 원가계산기")

# 비밀번호 보호 영역
password = st.text_input("접속 비밀번호를 입력하세요", type="password")
if password != "wetwipe123":
    st.warning("올바른 비밀번호를 입력하세요.")
    st.stop()

with st.form("calc_form"):
    st.subheader("📥 기본 입력값")
    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input("가로 길이 (mm)", value=150)
        gsm = st.number_input("평량 (g/㎡)", value=40)
        exchange_rate = st.number_input("환율 (₩/$)", value=1500)
    with col2:
        height = st.number_input("세로 길이 (mm)", value=195)
        tariff_percent = st.number_input("관세율 (%)", value=8)
        margin_rate = st.slider("마진율 (%)", 0, 50, 10) / 100

    submitted = st.form_submit_button("계산하기")

if submitted:
    tariff_rate = tariff_percent / 100
    result = calculate_wetwipe_cost(width, height, gsm, exchange_rate, tariff_rate, margin_rate=margin_rate)
    st.subheader("💡 계산 결과")
    for k, v in result.items():
        st.write(f"**{k}**: {v} 원")
