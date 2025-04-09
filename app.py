
# Streamlit 기반 물티슈 원가계산 웹 앱
import streamlit as st

def calculate_wetwipe_cost(width_mm, height_mm, gsm, quantity_per_unit=120, margin_rate=0.10):
    area_m2 = (width_mm / 1000) * (height_mm / 1000)
    unit_price_per_gsm = 3.07476
    loss_rate = 0.05
    applied_unit_price = unit_price_per_gsm * (1 + loss_rate)
    fabric_cost_per_sheet = area_m2 * gsm * applied_unit_price
    fabric_cost_total = fabric_cost_per_sheet * quantity_per_unit

    submaterials = {
        "정제수": 1.20,
        "파우치(SPC팩)": 56.24,
        "캡스티커": 19.16,
        "캡": 33.33,
        "이너스티커": 18.54,
        "박스": 77.77
    }

    processing_costs = {
        "물류비": 28.57,
        "노무비": 23.42,
        "4대보험+퇴직금": 4.17,
        "제조경비": 21.26,
        "이자비용": 17.01
    }

    materials_total = fabric_cost_total + sum(submaterials.values())
    processing_total = sum(processing_costs.values())
    total_cost = materials_total + processing_total

    margin = total_cost * margin_rate
    final_price = round(total_cost + margin, -1)

    cost_summary = {
        "원단(Sateri)": round(fabric_cost_total, 2),
        **submaterials,
        **processing_costs,
        "총원가": round(total_cost, 2),
        "마진({}%)".format(int(margin_rate * 100)): round(margin, 2),
        "제안가(판매가)": final_price
    }

    return cost_summary

# Streamlit UI
st.set_page_config(page_title="물티슈 원가계산기", layout="centered")
st.title("📦 물티슈 원가계산기")

with st.form("calc_form"):
    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input("가로 길이 (mm)", value=150)
        gsm = st.number_input("평량 (g/㎡)", value=40)
    with col2:
        height = st.number_input("세로 길이 (mm)", value=195)
        margin_rate = st.slider("마진율 (%)", 0, 50, 10) / 100

    submitted = st.form_submit_button("계산하기")

if submitted:
    result = calculate_wetwipe_cost(width, height, gsm, margin_rate=margin_rate)
    st.subheader("💡 계산 결과")
    for k, v in result.items():
        st.write(f"**{k}**: {v} 원")
