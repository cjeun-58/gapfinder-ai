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

# --- 1. 페이지 설정 및 데이터 초기화 ---
st.set_page_config(page_title="GapFinder AI v11.0", layout="wide")

# 세션 데이터 초기화 (분석 결과 휘발 방지)
states = ['brand_text', 'brand_insight', 'brand_analysis', 'comp_analysis', 
          'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key or 'insight' in key else []

# --- 2. 사이드바 (실시간 현황 체크) ---
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

# --- 3. 무결점 PDF 생성 함수 (글자 잘림 및 None 방지) ---
def generate_final_pdf(export_list):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
    has_font = os.path.exists(f_reg) and os.path.exists(f_bold)
    
    if has_font:
        pdf.add_font('NG', '', f_reg)
        pdf.add_font('NG', 'B', f_bold)
        pdf.set_font('NG', size=11)
    else:
        pdf.set_font("Arial", size=10)

    # 타이틀
    pdf.set_font('NG', 'B', 18) if has_font else pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 15, txt="Strategic Gap Analysis Report", ln=True, align='C')
    pdf.ln(5)

    for title, body in export_list:
        if body:
            # 섹션 헤더
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('NG', 'B', 13) if has_font else pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 10, txt=f"> {title}", ln=True, fill=True)
            pdf.ln(3)
            
            # 본문 (글자 잘림 방지를 위해 표 대신 리스트/텍스트 블록 사용)
            pdf.set_font('NG', '', 10) if has_font else pdf.set_font("Arial", size=10)
            pdf.set_text_color(50, 50, 50)
            
            # 특수기호 정제 (인코딩 에러 방지)
            safe_text = body.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-').replace('|', ' ')
            pdf.multi_cell(0, 7, txt=safe_text)
            pdf.ln(8)
            
    # output() 결과를 명시적으로 bytes로 변환하여 None 출력을 방지
    return bytes(pdf.output())

def analyze_ai(content, target_type, insight=""):
    try:
        client = genai.Client(api_key=gemini_key)
        p_base = "인사말이나 자기소개는 생략하고 분석 내용만 리스트 형식으로 작성하세요. 표(|)는 절대 사용하지 마세요.\n\n"
        
        if target_type == "brand":
            p = f"{p_base}자사 분석과 [운영 인사이트]를 반영하세요. 인사이트: {insight}"
        elif target_type == "final":
            p = f"{p_base}자사/경쟁사/소비자 데이터를 대조하여 필승 전략을 도출하세요. 인사이트: {insight}"
        else:
            p = f"{p_base}{target_type} 데이터를 기획서용으로 분석하세요."
        
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=p + "\n\n데이터:\n" + content[:8000])
        return response.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 단계별 실행 로직 ---

if menu == "STEP 1. 자사 분석 & 인사이트":
    st.title("🏢 STEP 1. 자사 분석 및 운영 인사이트")
    f = st.file_uploader("자료 업로드", accept_multiple_files=True)
    u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 운영 인사이트 (예: 특정 소구 효율 저조 등)", value=st.session_state['brand_insight'])
    
    if st.button("분석 실행"):
        if not gemini_key: st.error("Gemini Key 필수"); st.stop()
        with st.spinner("분석 중..."):
            raw_text = u + "\n" + st.session_state['brand_insight']
            if f:
                for file in f:
                    if file.name.endswith(".pdf"): raw_text += "\n".join([p.extract_text() for p in PdfReader(file).pages])
            st.session_state['brand_analysis'] = analyze_ai(raw_text, "brand", st.session_state['brand_insight'])
            st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 분석":
    st.title("⚔️ STEP 1.5. 경쟁사 분석")
    cn = st.text_input("경쟁사 브랜드명")
    if st.button("경쟁사 분석 실행"):
        if not serper_key: st.error("Serper Key 필수"); st.stop()
        with st.spinner("경쟁사 탐색 중..."):
            res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{cn} 특징", "gl": "kr", "hl": "ko"}).json()
            info = "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
            st.session_state['comp_analysis'] = analyze_ai(info, "comp")
            st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 분석":
    st.title("👥 STEP 2. 소비자 리얼 보이스 분석")
    kw = st.text_input("키워드")
    if st.button("수집 및 분석"):
        if not serper_key: st.error("Serper Key 필수"); st.stop()
        with st.spinner("데이터 수집 중..."):
            res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": kw + " 후기", "gl": "kr", "hl": "ko"}).json()
            data = [{'title': r.get('title'), 'body': r.get('snippet')} for r in res.get('organic', [])]
            st.session_state['consumer_data'] = data
            st.session_state['consumer_analysis'] = analyze_ai(str(data), "consumer")
            st.rerun()
    if st.session_state['consumer_analysis']:
        st.markdown(st.session_state['consumer_analysis'])
        st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 전략 및 통합 PDF":
    st.title("🧠 STEP 3. 최종 전략 및 통합 리포트")
    if st.button("🚀 최종 필승 전략 도출"):
        with st.spinner("간극 분석 중..."):
            d = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_ai(d, "final", st.session_state['brand_insight'])
            st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        st.subheader("📥 리포트 다운로드 설정")
        
        # 체크박스 선택 (None 출력이 없도록 개별 변수에 할당)
        c1, c2, c3, c4 = st.columns(4)
        with c1: i1 = st.checkbox("자사 분석", value=True)
        with c2: i2 = st.checkbox("경쟁사 분석", value=True)
        with c3: i3 = st.checkbox("소비자 분석", value=True)
        with c4: i4 = st.checkbox("최종 전략", value=True)
        
        export_list = []
        if i1: export_list.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
        if i2: export_list.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
        if i3: export_list.append(("CONSUMER ANALYSIS", st.session_state['consumer_analysis']))
        if i4: export_list.append(("FINAL STRATEGY", st.session_state['final_report']))
        
        if export_list:
            # [수정] PDF 생성을 미리 수행하고 바이너리 데이터를 버튼에 바로 전달
            pdf_bytes = generate_final_pdf(export_list)
            st.download_button(
                label="📥 통합 리포트 PDF 다운로드 (One-Click)",
                data=pdf_bytes,
                file_name="Total_Strategy_Report.pdf",
                mime="application/pdf"
            )
