import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io
import os
import re

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="GapFinder AI v11.5", layout="wide")

# 세션 데이터 초기화
states = ['brand_text', 'brand_insight', 'brand_analysis', 'comp_analysis', 
          'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key or 'insight' in key else []

# --- 2. 사이드바 (실시간 현황) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", ["STEP 1. 자사 분석 & 인사이트", "STEP 1.5. 경쟁사 분석", "STEP 2. 소비자 분석", "STEP 3. 전략 및 통합 PDF"])
    st.divider()
    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 자사: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. PDF 엔진 (None 출력 차단) ---
def generate_clean_pdf(export_list):
    pdf = FPDF()
    _ = pdf.set_auto_page_break(auto=True, margin=15)
    _ = pdf.add_page()
    
    f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
    has_font = os.path.exists(f_reg) and os.path.exists(f_bold)
    
    if has_font:
        _ = pdf.add_font('NG', '', f_reg)
        _ = pdf.add_font('NG', 'B', f_bold)
        _ = pdf.set_font('NG', size=11)
    else:
        _ = pdf.set_font("Arial", size=10)

    # 타이틀 설정
    _ = pdf.set_font('NG', 'B', 18) if has_font else pdf.set_font("Arial", 'B', 14)
    _ = pdf.set_text_color(0, 51, 102)
    _ = pdf.cell(0, 15, txt="Strategic Gap Analysis Report", ln=True, align='C')
    _ = pdf.ln(5)

    for title, body in export_list:
        if body:
            # 섹션 제목 (None 방지를 위해 모든 호출을 _ 에 할당)
            _ = pdf.set_fill_color(240, 240, 240)
            _ = pdf.set_font('NG', 'B', 13) if has_font else pdf.set_font("Arial", 'B', 11)
            _ = pdf.cell(0, 10, txt=f"> {title}", ln=True, fill=True)
            _ = pdf.ln(3)
            
            # 본문 설정
            _ = pdf.set_font('NG', '', 10) if has_font else pdf.set_font("Arial", size=10)
            _ = pdf.set_text_color(50, 50, 50)
            
            safe_text = body.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-').replace('|', ' ')
            clean_text = re.sub(r'[^\u0000-\u007f\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7af\ud7b0-\ud7ff]', '', safe_text)
            
            _ = pdf.multi_cell(0, 7, txt=clean_text)
            _ = pdf.ln(8)
            
    return bytes(pdf.output())

# --- 4. 분석 엔진 ---
def analyze_ai(content, target_type, insight=""):
    try:
        client = genai.Client(api_key=gemini_key)
        p_base = "인사말이나 자기소개는 생략하고 분석 내용만 리스트 형식으로 작성하세요. 표(|)는 절대 사용하지 마세요.\n\n"
        
        if target_type == "brand":
            p = f"{p_base}자사 분석과 [운영 인사이트]를 반영하세요. 인사이트: {insight}"
        elif target_type == "final":
            p = f"{p_base}자사/경쟁사/소비자 데이터를 대조하여 필승 전략을 도출하세요. 인사이트: {insight}"
        else:
            p = f"{p_base}{target_type} 데이터를 분석하세요."
        
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=p + "\n\n데이터:\n" + content[:8000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 5. 단계별 실행 로직 ---

if menu == "STEP 1. 자사 분석 & 인사이트":
    st.title("🏢 자사 분석 및 운영 인사이트")
    f = st.file_uploader("자료 업로드", accept_multiple_files=True)
    u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 운영 인사이트", value=st.session_state['brand_insight'])
    
    if st.button("분석 실행"):
        _ = st.spinner("분석 중...")
        raw_text = u + "\n" + st.session_state['brand_insight']
        if f:
            for file in f:
                if file.name.endswith(".pdf"): raw_text += "\n".join([p.extract_text() for p in PdfReader(file).pages])
        st.session_state['brand_analysis'] = analyze_ai(raw_text, "brand", st.session_state['brand_insight'])
        _ = st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 분석":
    st.title("⚔️ 경쟁사 전략 분석")
    cn = st.text_input("경쟁사 브랜드명")
    if st.button("경쟁사 분석 실행"):
        _ = st.spinner("탐색 중...")
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{cn} 특징", "gl": "kr", "hl": "ko"}).json()
        info = "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
        st.session_state['comp_analysis'] = analyze_ai(info, "comp")
        _ = st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 분석":
    st.title("👥 소비자 리얼 보이스 분석")
    kw = st.text_input("키워드")
    if st.button("수집 및 분석"):
        _ = st.spinner("수집 중...")
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": kw + " 후기", "gl": "kr", "hl": "ko"}).json()
        data = [{'title': r.get('title'), 'body': r.get('snippet')} for r in res.get('organic', [])]
        st.session_state['consumer_data'] = data
        st.session_state['consumer_analysis'] = analyze_ai(str(data), "consumer")
        _ = st.rerun()
    if st.session_state['consumer_analysis']:
        st.markdown(st.session_state['consumer_analysis'])
        st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 전략 및 통합 PDF":
    st.title("🧠 최종 전략 및 통합 리포트")
    if st.button("🚀 최종 전략 도출"):
        _ = st.spinner("전략 수립 중...")
        d = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
        st.session_state['final_report'] = analyze_ai(d, "final", st.session_state['brand_insight'])
        _ = st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        st.subheader("📥 리포트 다운로드 설정")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: i1 = st.checkbox("자사 분석 포함", value=True)
        with c2: i2 = st.checkbox("경쟁사 분석 포함", value=True)
        with c3: i3 = st.checkbox("소비자 분석 포함", value=True)
        with c4: i4 = st.checkbox("최종 전략 포함", value=True)
        
        export_list = []
        # append 결과(None)가 노출되지 않도록 처리
        if i1: _ = export_list.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
        if i2: _ = export_list.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
        if i3: _ = export_list.append(("CONSUMER ANALYSIS", st.session_state['consumer_analysis']))
        if i4: _ = export_list.append(("FINAL STRATEGY", st.session_state['final_report']))
        
        if export_list:
            pdf_bytes = generate_clean_pdf(export_list)
            st.download_button(
                label="📥 리포트 PDF 다운로드 (One-Click)",
                data=pdf_bytes,
                file_name="Total_Strategy_Report.pdf",
                mime="application/pdf"
            )
