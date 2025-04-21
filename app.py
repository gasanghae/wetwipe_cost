# Streamlit 기반 물티슈 원가계산 웹 앱
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import os
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import datetime
import gspread
from google.oauth2.service_account import Credentials

# 한글 깨짐 방지용 폰트 설정
import matplotlib
matplotlib.rcParams['font.family'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans']

def calculate_wetwipe_cost(width_mm, height_mm, gsm, exchange_rate, percent_applied, quantity_per_unit, margin_rate=0.10,
                             labor_cost=23.42, insurance_cost=4.17, management_cost=21.26, interest_cost=17.01, storage_cost=5.00, logistics_cost=28.57, usd_price_per_kg=1.46,
                             submaterials=None, processing_costs=None, other_costs=None, corporate_profit=100):
    area_m2 = (width_mm / 1000) * (height_mm / 1000)
    applied_usd_price = usd_price_per_kg * percent_applied
    unit_price_per_g = applied_usd_price * exchange_rate / 1000
    gsm_price = unit_price_per_g * gsm
    loss_rate_fabric = 0.05
    applied_unit_price = gsm_price * (1 + loss_rate_fabric)
    fabric_cost_per_sheet = area_m2 * applied_unit_price
    fabric_cost_total = fabric_cost_per_sheet * quantity_per_unit

    fabric_unit_price_per_sheet = round(fabric_cost_per_sheet, 4)
    fabric_unit_cost = round(fabric_cost_total, 2)
    
    # 기초가격 계산
    base_price = usd_price_per_kg * exchange_rate * percent_applied

    # 기본 submaterials 값 설정
    if submaterials is None:
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

    # 기본 processing_costs 값 설정
    if processing_costs is None:
        processing_costs = {
            "물류비": logistics_cost,
            "노무비": labor_cost,
            "4대보험+퇴직금": insurance_cost,
            "제조경비": management_cost,
            "이자비용": interest_cost,
            "창고료": storage_cost
        }
        
    # 기본 other_costs 값 설정
    if other_costs is None:
        other_costs = {
            "택배비": 0.00,
            "광고선전비": 0.00,
            "부가세": 0.00
        }

    materials_total = fabric_cost_total + sum(submaterials.values())
    processing_total = sum(processing_costs.values())
    other_total = sum(other_costs.values())
    total_cost = materials_total + processing_total + other_total

    margin = total_cost * margin_rate
    final_price = total_cost + margin + corporate_profit

    cost_summary = {
        "원단 가격": fabric_unit_cost,
        "기초가격": round(base_price, 2),
        **submaterials,
        "-- 원부자재 소계": round(materials_total, 2),
        **processing_costs,
        "-- 임가공비 소계": round(processing_total, 2),
        **other_costs,
        "-- 기타 비용 소계": round(other_total, 2),
        "총원가": round(total_cost, 2),
        "마진({}%)".format(int(margin_rate * 100)): round(margin, 2),
        "기업이윤": corporate_profit,
        "제안가(판매가)": round(final_price, 2)
    }

    return cost_summary, fabric_unit_price_per_sheet, submaterials, processing_costs, other_costs, final_price, base_price

st.set_page_config(page_title="물티슈 원가계산기", layout="centered")
st.title("📦 물티슈 원가계산기")

if 'restore_data' in st.session_state:
    restore = st.session_state.restore_data
    width = int(restore.get("규격", "150x195").split("x")[0])
    height = int(restore.get("규격", "150x195").split("x")[1])
    gsm = int(restore.get("평량", 40))
    quantity = int(restore.get("매수", 100))
    exchange_rate = float(restore.get("환율", 1500))
    percent_applied = float(restore.get("관세비율", 1.2))
    margin_rate = float(restore.get("마진율", 0.1))
else:
    width, height, gsm, quantity, exchange_rate, percent_applied, margin_rate = 150, 195, 40, 120, 1500, 1.2, 0.1

with st.form("calc_form"):
    st.subheader("📥 기본 입력값")
    
    # 견적명
    estimate_name = st.text_input("견적명", value="")
    
    # 원단 정보
    st.markdown("### 원단 정보")
    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input("원단 가로길이 (mm)", value=150)
        gsm = st.number_input("평량 (g/㎡)", value=40)
        usd_price_per_kg = st.number_input("원단 가격 ($/kg)", value=1.46)
    with col2:
        height = st.number_input("원단 세로길이 (mm)", value=195)
        quantity = st.number_input("수량 (매수)", value=100)
        exchange_rate = st.number_input("환율 (₩/$)", value=1500)
        percent_applied = st.number_input("관세 포함 비율 (%)", value=120) / 100
    
    # 원부자재 비용
    st.markdown("### 원부자재 비용")
    submaterials = {
        "정제수": st.number_input("정제수 (원)", value=1.20, format="%.4f"),
        "명진 메인": st.number_input("명진 메인 (원)", value=15.41, format="%.4f"),
        "명진 소듐": st.number_input("명진 소듐 (원)", value=7.40, format="%.4f"),
        "명진 인산": st.number_input("명진 인산 (원)", value=1.39, format="%.4f"),
        "SPC팩(파우치)": st.number_input("SPC팩(파우치) (원)", value=56.24, format="%.4f"),
        "영신피엔엘(캡스티커)": st.number_input("영신피엔엘(캡스티커) (원)", value=19.16, format="%.4f"),
        "나우텍(캡)": st.number_input("나우텍(캡) (원)", value=33.33, format="%.4f"),
        "영신피엔엘(이너스티커)": st.number_input("영신피엔엘(이너스티커) (원)", value=18.54, format="%.4f"),
        "지피엠(박스)": st.number_input("지피엠(박스) (원)", value=77.77, format="%.4f")
    }
    
    # 임가공비
    st.markdown("### 임가공비")
    processing_costs = {
        "물류비": st.number_input("물류비 (원)", value=28.57, format="%.4f"),
        "노무비": st.number_input("노무비 (원)", value=23.42, format="%.4f"),
        "4대보험+퇴직금": st.number_input("4대보험+퇴직금 (원)", value=4.17, format="%.4f"),
        "제조경비": st.number_input("제조경비 (원)", value=21.26, format="%.4f"),
        "이자비용": st.number_input("이자비용 (원)", value=17.01, format="%.4f"),
        "창고료": st.number_input("창고료 (원)", value=5.10, format="%.4f")
    }
    
    # 기타 비용
    st.markdown("### 기타 비용")
    col3, col4 = st.columns(2)
    with col3:
        other_cost_names = {
            "cost1": st.text_input("기타 비용 항목 1", value="택배비"),
            "cost2": st.text_input("기타 비용 항목 2", value="광고선전비"),
            "cost3": st.text_input("기타 비용 항목 3", value="부가세")
        }
    with col4:
        other_cost_values = {
            other_cost_names["cost1"]: st.number_input("금액 1 (원)", value=0.00, format="%.4f"),
            other_cost_names["cost2"]: st.number_input("금액 2 (원)", value=0.00, format="%.4f"),
            other_cost_names["cost3"]: st.number_input("금액 3 (원)", value=0.00, format="%.4f")
        }
    
    # 마진율과 기업이윤
    col5, col6 = st.columns(2)
    with col5:
        margin_rate = st.slider("마진율 (%)", 0, 50, 10) / 100
    with col6:
        corporate_profit = st.number_input("기업이윤 (원)", value=100.00, format="%.4f")
    
    submitted = st.form_submit_button("📊 계산하기")

if submitted:
    result, unit_price, submaterials, processing_costs, other_costs, final_price, base_price = calculate_wetwipe_cost(
        width, height, gsm, exchange_rate, percent_applied, quantity,
        margin_rate=margin_rate,
        usd_price_per_kg=usd_price_per_kg,
        submaterials=submaterials,
        processing_costs=processing_costs,
        other_costs=other_cost_values,
        corporate_profit=corporate_profit
    )

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("Wetwipe Estimates").worksheet("Sheet1")
    
    # 헤더 설정
    headers = [
        "견적명", "규격", "평량", "매수", "환율", "관세비율", "총원가", "제안가",
        "원단 가격", "기초가격", "정제수", "명진 메인", "명진 소듐", "명진 인산",
        "SPC팩(파우치)", "영신피엔엘(캡스티커)", "나우텍(캡)", "영신피엔엘(이너스티커)",
        "지피엠(박스)", "물류비", "노무비", "4대보험+퇴직금", "제조경비", "이자비용",
        "창고료", other_cost_names["cost1"], other_cost_names["cost2"], other_cost_names["cost3"],
        "마진율", "기업이윤"
    ]
    
    if not sheet.row_values(1):
        sheet.insert_row(headers, 1)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "견적명": estimate_name if estimate_name else "자동저장견적",
        "규격": f"{width}x{height}",
        "평량": gsm,
        "매수": quantity,
        "환율": exchange_rate,
        "관세비율": percent_applied,
        "총원가": result["총원가"],
        "제안가": result["제안가(판매가)"],
        "원단 가격": result["원단 가격"],
        "기초가격": result["기초가격"],
        "정제수": result["정제수"],
        "명진 메인": result["명진 메인"],
        "명진 소듐": result["명진 소듐"],
        "명진 인산": result["명진 인산"],
        "SPC팩(파우치)": result["SPC팩(파우치)"],
        "영신피엔엘(캡스티커)": result["영신피엔엘(캡스티커)"],
        "나우텍(캡)": result["나우텍(캡)"],
        "영신피엔엘(이너스티커)": result["영신피엔엘(이너스티커)"],
        "지피엠(박스)": result["지피엠(박스)"],
        "물류비": result["물류비"],
        "노무비": result["노무비"],
        "4대보험+퇴직금": result["4대보험+퇴직금"],
        "제조경비": result["제조경비"],
        "이자비용": result["이자비용"],
        "창고료": result["창고료"],
        other_cost_names["cost1"]: result[other_cost_names["cost1"]],
        other_cost_names["cost2"]: result[other_cost_names["cost2"]],
        other_cost_names["cost3"]: result[other_cost_names["cost3"]],
        "마진율": margin_rate,
        "기업이윤": corporate_profit
    }

    # 스프레드시트에 저장할 때는 리스트로 변환
    row_values = [row[header] for header in headers]
    sheet.append_row(row_values)

    # 계산 결과를 session_state에 저장
    st.session_state.result = result
    st.session_state.unit_price = unit_price
    st.session_state.submaterials = submaterials
    st.session_state.processing_costs = processing_costs
    st.session_state.other_costs = other_costs
    st.session_state.other_cost_names = other_cost_names
    st.session_state.row = row
    st.session_state.calculated = True

    st.success("견적이 Google Sheets에 자동 저장되었습니다!")

# 계산 결과 표시
if 'calculated' in st.session_state and st.session_state.calculated:
    st.subheader("💡 계산 결과")
    
    # 기본 정보
    st.markdown("### 📊 기본 정보")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
            <h4 style='color: #262730; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;'>원단 정보</h4>
            <div style='display: flex; justify-content: space-between; margin: 10px 0;'>
                <span style='font-weight: bold;'>원단 단가 (1장당)</span>
                <span style='color: #1f77b4;'>{:,} 원</span>
            </div>
            <div style='display: flex; justify-content: space-between; margin: 10px 0;'>
                <span style='font-weight: bold;'>총원가</span>
                <span style='color: #1f77b4;'>{:,} 원</span>
            </div>
        </div>
        """.format(
            st.session_state.unit_price,
            st.session_state.result["총원가"]
        ), unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
            <h4 style='color: #262730; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;'>가격 정보</h4>
            <div style='display: flex; justify-content: space-between; margin: 10px 0;'>
                <span style='font-weight: bold;'>제안가(판매가)</span>
                <span style='color: #1f77b4;'>{:,} 원</span>
            </div>
            <div style='display: flex; justify-content: space-between; margin: 10px 0;'>
                <span style='font-weight: bold;'>마진({}%)</span>
                <span style='color: #1f77b4;'>{:,} 원</span>
            </div>
        </div>
        """.format(
            st.session_state.result["제안가(판매가)"],
            int(st.session_state.row["마진율"] * 100),
            st.session_state.result["마진({}%)".format(int(st.session_state.row["마진율"] * 100))]
        ), unsafe_allow_html=True)

    # 비용 구성
    st.markdown("### 📈 비용 구성")
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
            <h4 style='color: #262730; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;'>원부자재 소계</h4>
            <div style='display: flex; justify-content: space-between; margin: 10px 0;'>
                <span style='font-weight: bold;'>금액</span>
                <span style='color: #1f77b4;'>{:,} 원</span>
            </div>
        </div>
        """.format(st.session_state.result["-- 원부자재 소계"]), unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
            <h4 style='color: #262730; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;'>임가공비 소계</h4>
            <div style='display: flex; justify-content: space-between; margin: 10px 0;'>
                <span style='font-weight: bold;'>금액</span>
                <span style='color: #1f77b4;'>{:,} 원</span>
            </div>
        </div>
        """.format(st.session_state.result["-- 임가공비 소계"]), unsafe_allow_html=True)

    # 상세 내역
    st.markdown("### 📋 상세 내역")
    
    # 원단 비용
    st.markdown("""
    <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h4 style='color: #262730; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;'>원단 비용</h4>
        <div style='display: flex; justify-content: space-between; margin: 10px 0; padding: 10px; background-color: white; border-radius: 6px;'>
            <span style='font-weight: bold;'>원단 가격</span>
            <span style='color: #1f77b4;'>{:,} 원</span>
        </div>
        <div style='display: flex; justify-content: space-between; margin: 10px 0; padding: 10px; background-color: white; border-radius: 6px;'>
            <span style='font-weight: bold;'>기초가격 (롤,Kg,개/원)</span>
            <span style='color: #1f77b4;'>{:,} 원</span>
        </div>
    </div>
    """.format(
        st.session_state.result["원단 가격"],
        st.session_state.result["기초가격"]
    ), unsafe_allow_html=True)
    
    # 원부자재 비용
    st.markdown("""
    <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h4 style='color: #262730; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;'>원부자재 비용</h4>
    """, unsafe_allow_html=True)
    for item, cost in st.session_state.submaterials.items():
        st.markdown(f"""
        <div style='display: flex; justify-content: space-between; margin: 10px 0; padding: 10px; background-color: white; border-radius: 6px;'>
            <span style='font-weight: bold;'>{item}</span>
            <span style='color: #1f77b4;'>{cost:,} 원</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 임가공비
    st.markdown("""
    <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h4 style='color: #262730; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;'>임가공비</h4>
    """, unsafe_allow_html=True)
    for item, cost in st.session_state.processing_costs.items():
        st.markdown(f"""
        <div style='display: flex; justify-content: space-between; margin: 10px 0; padding: 10px; background-color: white; border-radius: 6px;'>
            <span style='font-weight: bold;'>{item}</span>
            <span style='color: #1f77b4;'>{cost:,} 원</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # PDF 저장
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    import matplotlib.font_manager as fm

    # 한글 폰트 설정
    nanum_font_path = fm.findfont("NanumGothic")
    pdfmetrics.registerFont(TTFont("NanumGothic", nanum_font_path))
    pdfmetrics.registerFont(UnicodeCIDFont("HYGothic-Medium"))

    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    c.setFont("NanumGothic", 12)

    # PDF 디자인 개선
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont("NanumGothic", 16)
    c.drawString(50, 800, "📄 물티슈 원가계산 결과")

    c.setFont("NanumGothic", 12)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    y = 760
    for k, v in st.session_state.result.items():
        c.drawString(50, y, f"{k}: {v:,} 원")
        y -= 20
        if y < 50:
            c.showPage()
            c.setFont("NanumGothic", 12)
            y = 800

    c.save()
    st.download_button(
        "📄 PDF로 다운로드", 
        data=pdf_buffer.getvalue(), 
        file_name="wetwipe_cost.pdf",
        key="pdf_download"
    )

    # Excel 저장
    df_result = pd.DataFrame(st.session_state.result.items(), columns=["항목", "금액 (원)"])
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        df_result.to_excel(writer, index=False, sheet_name="견적서")
        worksheet = writer.sheets["견적서"]
        worksheet.set_column('A:B', 30)  # 열 너비 조정
    st.download_button(
        "📥 Excel로 다운로드", 
        data=excel_buffer.getvalue(), 
        file_name="wetwipe_cost.xlsx",
        key="excel_download"
    )

    # 시각화
    st.subheader("📊 원가 구성 시각화")
    
    # 전체 비용 구성 파이 차트
    st.markdown("#### 전체 비용 구성")
    total_costs = {
        "원단": st.session_state.result["원단 가격"],
        "원부자재": sum(st.session_state.submaterials.values()),
        "임가공비": sum(st.session_state.processing_costs.values())
    }
    
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.pie(total_costs.values(), labels=total_costs.keys(), autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')
    st.pyplot(fig1)
    
    # 원부자재 비용 구성
    st.markdown("#### 원부자재 비용 구성")
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    submaterials_data = pd.DataFrame({
        "항목": list(st.session_state.submaterials.keys()),
        "비용": list(st.session_state.submaterials.values())
    })
    submaterials_data = submaterials_data.sort_values("비용", ascending=True)
    ax2.barh(submaterials_data["항목"], submaterials_data["비용"], color="skyblue")
    ax2.set_xlabel("비용 (원)")
    ax2.set_title("원부자재 항목별 비용")
    for i, v in enumerate(submaterials_data["비용"]):
        ax2.text(v, i, f"{v:,.2f} 원", va='center')
    st.pyplot(fig2)
    
    # 임가공비 구성
    st.markdown("#### 임가공비 구성")
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    processing_data = pd.DataFrame({
        "항목": list(st.session_state.processing_costs.keys()),
        "비용": list(st.session_state.processing_costs.values())
    })
    processing_data = processing_data.sort_values("비용", ascending=True)
    ax3.barh(processing_data["항목"], processing_data["비용"], color="lightgreen")
    ax3.set_xlabel("비용 (원)")
    ax3.set_title("임가공비 항목별 비용")
    for i, v in enumerate(processing_data["비용"]):
        ax3.text(v, i, f"{v:,.2f} 원", va='center')
    st.pyplot(fig3)
    
    # 비용 상세 테이블
    st.markdown("#### 비용 상세 내역")
    cost_details = pd.DataFrame({
        "항목": ["원단 가격"] + list(st.session_state.submaterials.keys()) + list(st.session_state.processing_costs.keys()),
        "비용": [st.session_state.result["원단 가격"]] + list(st.session_state.submaterials.values()) + list(st.session_state.processing_costs.values())
    })
    cost_details["비율"] = (cost_details["비용"] / sum(cost_details["비용"]) * 100).round(2)
    cost_details = cost_details.sort_values("비용", ascending=False)
    st.dataframe(cost_details.style.format({
        "비용": "{:,.2f} 원",
        "비율": "{:.2f}%"
    }))

    # 사이드바 복원 기능
    if st.sidebar.button("📂 지난 견적 불러오기"):
        st.subheader("📋 저장된 견적 목록 및 복원")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Wetwipe Estimates").sheet1
        df_log = pd.DataFrame(sheet.get_all_records())
        st.dataframe(df_log)
        
        selected_row = st.selectbox("📌 복원할 견적 선택 (번호)", df_log.index)
        if st.button("📤 이 견적으로 계산기 채우기"):
            selected_data = df_log.loc[selected_row]
            st.session_state.restore_data = {
                "견적명": selected_data["견적명"],
                "규격": selected_data["규격"],
                "평량": selected_data["평량"],
                "매수": selected_data["매수"],
                "환율": selected_data["환율"],
                "관세비율": selected_data["관세비율"],
                "마진율": selected_data["마진율"],
                "기업이윤": selected_data["기업이윤"],
                "원단 가격": selected_data["원단 가격"],
                "기초가격": selected_data["기초가격"],
                "정제수": selected_data["정제수"],
                "명진 메인": selected_data["명진 메인"],
                "명진 소듐": selected_data["명진 소듐"],
                "명진 인산": selected_data["명진 인산"],
                "SPC팩(파우치)": selected_data["SPC팩(파우치)"],
                "영신피엔엘(캡스티커)": selected_data["영신피엔엘(캡스티커)"],
                "나우텍(캡)": selected_data["나우텍(캡)"],
                "영신피엔엘(이너스티커)": selected_data["영신피엔엘(이너스티커)"],
                "지피엠(박스)": selected_data["지피엠(박스)"],
                "물류비": selected_data["물류비"],
                "노무비": selected_data["노무비"],
                "4대보험+퇴직금": selected_data["4대보험+퇴직금"],
                "제조경비": selected_data["제조경비"],
                "이자비용": selected_data["이자비용"],
                "창고료": selected_data["창고료"],
                "기타비용1": selected_data[df_log.columns[-3]],
                "기타비용2": selected_data[df_log.columns[-2]],
                "기타비용3": selected_data[df_log.columns[-1]]
            }
            st.experimental_rerun()
