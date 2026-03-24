import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io
import time
import os

# --- 1. 페이지 설정 및 데이터 초기화 ---
st.set_page_config(page_title="GapFinder AI v9.0", layout="wide")

# 분석 상태 및 데이터 저장용 세션 (데이터 휘발 방지)
states = ['brand_text', 'brand_insight', 'brand_analysis', 'comp_analysis', 
          'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key or 'insight' in key else []

# --- 2. 사이드바 (API 설정 및 현황 체크) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 자사 분석 & 인사이트", 
        "STEP 1.5. 경쟁사 분석", 
        "STEP 2. 소비자 분석", 
        "STEP 3. 전략 및 통합 PDF"
    ])
    st.divider()

    # [복구] 실시간 분석 현황 체크표시
    st.subheader("📊 실시간 분석 현황")
    b_check = "✅ 완료" if st.session_state['brand_analysis'] else "❌ 미완료"
    c_check = "✅ 완료" if st.session_state['comp_analysis'] else "❌ 미완료"
    s_check = "✅ 완료" if st.session_state['consumer_analysis'] else "❌ 미완료"
    st.write(f"🏢 자사: {b_check}")
    st.write(f"⚔️ 경쟁사: {c_check}")
    st.write(f"👥 소비자: {s_check}")

# --- 3. 안정적인 PDF 생성 함수 (글자 잘림 방지) ---
def generate_stable_pdf(export_list):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # 폰트 로드 (파일이 있을 경우에만)
    font_reg = "NanumGothic.ttf"
    font_bold = "NanumGothicBold.ttf"
    has_font = False
    try:
        if os.path.exists(font_reg) and os.path.exists(font_bold):
            pdf.add_font('NG', '', font_reg)
            pdf.add_font('NG', 'B', font_bold)
            pdf.set_font('NG', size=11)
            has_font = True
        else:
            pdf.set_font("Arial", size=10)
    except:
        pdf.set_font("Arial", size=10)

    # 리포트 제목
    pdf.set_font('NG', 'B', 16) if has_font else pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 15, txt="Strategic Gap Analysis Report", ln=True, align='C')
    pdf.ln(5)

    for title, body in export_list:
        if body:
            # 섹션 제목
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('NG', 'B', 12) if has_font else pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 10, txt=f"> {title}", ln=True, fill=True)
            pdf.ln(3)
            
            # 본문 (표 형식 제외, 순수 텍스트로만 안전하게 출력)
            pdf.set_font('NG', '', 10) if has_font else pdf.set_font("Arial", size=10)
            # 유니코드 에러 방지 처리
            safe_text = body.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-')
            # 마크다운 표 기호(|) 제거 (글자 잘림의 원인)
            safe_text = safe_text.replace('|', ' ')
            pdf.multi_cell(0, 7, txt=safe_text)
            pdf.ln(8)
            
    return bytes(pdf.output())

def analyze_ai(content, target_type, insight=""):
    try:
        client = genai.Client(api_key=gemini_key)
        # 자기소개 금지 및 형식 지정
        p_base = "인사말이나 자기소개 없이 바로 분석 내용만 작성하세요. 표(|) 형식은 사용하지 말고 리스트 형태로 작성하세요.\n\n"
        if target_type == "brand":
            p = f"{p_base}자사 분석과 [운영 인사이트]를 반영하세요. 인사이트: {insight}"
        elif target_type == "final":
            p = f"{p_base}자사/경쟁사/소비자 데이터를 대조하여 전략을 도출하세요. 인사이트: {insight}"
        else:
            p = f"{p_base}{target_type} 데이터를 분석하세요."
        
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=p + "\n\n데이터:\n" + content[:8000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 단계별 실행 로직 ---

# [STEP 1] 자사
if menu == "STEP 1. 자사 분석 & 인사이트":
    st.title("🏢 STEP 1. 자사 분석 및 운영 인사이트")
    f = st.file_uploader("자사 자료 업로드", accept_multiple_files=True)
    u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 실제 운영 피드백 (성공/실패 사례)", value=st.session_state['brand_insight'])
    
    if st.button("자사 분석 실행"):
        text = u + "\n" + st.session_state['brand_insight']
        if f:
            for file in f:
                if file.name.endswith(".pdf"): text += "\n".join([p.extract_text() for p in PdfReader(file).pages])
        st.session_state['brand_analysis'] = analyze_ai(text, "brand", st.session_state['brand_insight'])
        st.rerun()
    st.markdown(st.session_state['brand_analysis'])

# [STEP 1.5] 경쟁사
elif menu == "STEP 1.5. 경쟁사 분석":
    st.title("⚔️ STEP 1.5. 경쟁사 분석")
    cn = st.text_input("경쟁사 브랜드명")
    if st.button("경쟁사 분석 실행"):
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, 
                            json={"q": f"{cn} 특징 마케팅", "gl": "kr", "hl": "ko"}).json()
        info = "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
        st.session_state['comp_analysis'] = analyze_ai(info, "comp")
        st.rerun()
    st.markdown(st.session_state['comp_analysis'])

# [STEP 2] 소비자
elif menu == "STEP 2. 소비자 분석":
    st.title("👥 STEP 2. 소비자 분석 및 원본 데이터")
    kw = st.text_input("키워드")
    if st.button("데이터 수집"):
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, 
                            json={"q": kw + " 후기", "gl": "kr", "hl": "ko"}).json()
        data = [{'title': r.get('title'), 'body': r.get('snippet')} for r in res.get('organic', [])]
        st.session_state['consumer_data'] = data
        st.session_state['consumer_analysis'] = analyze_ai(str(data), "consumer")
        st.rerun()
    if st.session_state['consumer_analysis']:
        st.markdown(st.session_state['consumer_analysis'])
        st.subheader("🔍 수집 원본 데이터")
        st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

# [STEP 3] 전략 및 PDF
elif menu == "STEP 3. 전략 및 통합 PDF":
    st.title("🧠 STEP 3. 최종 전략 및 커스텀 PDF")
    if st.button("🚀 최종 전략 도출"):
        d = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
        st.session_state['final_report'] = analyze_ai(d, "final", st.session_state['brand_insight'])
        st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        st.subheader("📥 선택 다운로드 설정")
        c1, c2, col3, col4 = st.columns(4)
        with c1: i1 = st.checkbox("자사", value=True)
        with c2: i2 = st.checkbox("경쟁사", value=True)
        with col3: i3 = st.checkbox("소비자", value=True)
        with col4: i4 = st.checkbox("전략", value=True)
        
        export_list = []
        if i1: export_list.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
        if i2: export_list.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
        if i3: export_list.append(("CONSUMER ANALYSIS", st.session_state['consumer_analysis']))
        if i4: export_list.append(("FINAL STRATEGY", st.session_state['final_report']))
        
        if st.button("📑 통합 PDF 생성 및 다운로드"):
            pdf_data = generate_stable_pdf(export_list)
            st.download_button("📥 PDF 파일 받기", data=pdf_data, file_name="Strategy_Report.pdf", mime="application/pdf")
