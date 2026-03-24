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

# --- 1. 페이지 설정 및 데이터 초기화 ---
st.set_page_config(page_title="GapFinder AI v10.0", layout="wide")

# 분석 상태 및 데이터 저장 (데이터 휘발 방지)
states = ['brand_text', 'brand_insight', 'brand_analysis', 'comp_analysis', 
          'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key or 'insight' in key else []

# --- 2. 사이드바 (상태 체크) ---
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

# --- 3. 안정적인 PDF 생성 함수 (가독성 & 원클릭 최적화) ---
def generate_stable_pdf(export_list):
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

    pdf.set_font('NG', 'B', 16) if has_font else pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 15, txt="Strategic Gap Analysis Report", ln=True, align='C')
    pdf.ln(5)

    for title, body in export_list:
        if body:
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('NG', 'B', 12) if has_font else pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 10, txt=f"> {title}", ln=True, fill=True)
            pdf.ln(3)
            
            pdf.set_font('NG', '', 10) if has_font else pdf.set_font("Arial", size=10)
            # 글자 잘림 방지를 위해 마크다운 기호 및 표 기호 제거
            safe_text = body.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-').replace('|', ' ')
            pdf.multi_cell(0, 7, txt=safe_text)
            pdf.ln(8)
            
    return pdf.output()

def analyze_ai(content, target_type, insight=""):
    try:
        client = genai.Client(api_key=gemini_key)
        # 자기소개 금지 및 톤앤매너 고정
        p_base = "자기소개나 인사는 절대 하지 말고 분석 내용만 리스트 형식으로 작성하세요. 표(|) 형식은 절대 사용하지 마세요.\n\n"
        
        if target_type == "brand":
            p = f"{p_base}브랜드 자료와 [운영 인사이트]를 반영하세요. 인사이트: {insight}"
        elif target_type == "final":
            p = f"{p_base}자사/경쟁사/소비자 데이터를 대조하여 필승 전략을 도출하세요. 인사이트: {insight}"
        else:
            p = f"{p_base}{target_type} 데이터를 분석하세요."
        
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=p + "\n\n데이터:\n" + content[:8000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 메인 로직 ---

if menu == "STEP 1. 자사 분석 & 인사이트":
    st.title("🏢 STEP 1. 자사 분석 및 운영 인사이트")
    f = st.file_uploader("자사 자료 업로드", accept_multiple_files=True)
    u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 실제 운영 피드백 (예: 테크 부업 소구는 효율 낮음)", value=st.session_state['brand_insight'])
    
    if st.button("자사 분석 실행"):
        text = u + "\n" + st.session_state['brand_insight']
        if f:
            for file in f:
                if file.name.endswith(".pdf"): text += "\n".join([p.extract_text() for p in PdfReader(file).pages])
        st.session_state['brand_analysis'] = analyze_ai(text, "brand", st.session_state['brand_insight'])
        st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 분석":
    st.title("⚔️ STEP 1.5. 경쟁사 분석")
    cn = st.text_input("경쟁사 브랜드명")
    if st.button("경쟁사 분석 실행"):
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{cn} 특징", "gl": "kr", "hl": "ko"}).json()
        info = "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
        st.session_state['comp_analysis'] = analyze_ai(info, "comp")
        st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 분석":
    st.title("👥 STEP 2. 소비자 분석")
    kw = st.text_input("키워드")
    if st.button("데이터 수집"):
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": kw + " 후기", "gl": "kr", "hl": "ko"}).json()
        data = [{'title': r.get('title'), 'body': r.get('snippet')} for r in res.get('organic', [])]
        st.session_state['consumer_data'] = data
        st.session_state['consumer_analysis'] = analyze_ai(str(data), "consumer")
        st.rerun()
    if st.session_state['consumer_analysis']:
        st.markdown(st.session_state['consumer_analysis'])
        st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 전략 및 통합 PDF":
    st.title("🧠 STEP 3. 최종 전략 및 원클릭 PDF")
    if st.button("🚀 최종 전략 리포트 생성"):
        d = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
        st.session_state['final_report'] = analyze_ai(d, "final", st.session_state['brand_insight'])
        st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        st.subheader("📥 통합 리포트 다운로드")
        
        # [핵심] 체크박스 선택에 따라 미리 PDF 데이터를 준비함
        c1, c2, c3, c4 = st.columns(4)
        with c1: i1 = st.checkbox("자사 분석 포함", value=True)
        with c2: i2 = st.checkbox("경쟁사 분석 포함", value=True)
        with c3: i3 = st.checkbox("소비자 분석 포함", value=True)
        with c4: i4 = st.checkbox("최종 전략 포함", value=True)
        
        export_list = []
        if i1: export_list.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
        if i2: export_list.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
        if i3: export_list.append(("CONSUMER ANALYSIS", st.session_state['consumer_analysis']))
        if i4: export_list.append(("FINAL STRATEGY", st.session_state['final_report']))
        
        if export_list:
            # 버튼이 렌더링될 때 PDF 데이터를 바로 꽂아넣음 -> 한 번만 누르면 다운로드됨
            pdf_data = generate_stable_pdf(export_list)
            st.download_button(
                label="📥 리포트 PDF 다운로드 (One-Click)",
                data=bytes(pdf_data),
                file_name="Total_Strategy_Report.pdf",
                mime="application/pdf"
            )
