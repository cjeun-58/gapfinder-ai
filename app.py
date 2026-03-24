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

# --- 1. 기본 설정 및 데이터 초기화 ---
st.set_page_config(page_title="GapFinder AI v5.9", layout="wide")

for key in ['brand_text', 'brand_analysis', 'consumer_data', 'consumer_analysis', 'final_report']:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key else []

# --- 2. 사이드바 ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", ["STEP 1. 브랜드 보이스 분석", "STEP 2. 소비자 리얼 보이스 탐색", "STEP 3. 전략적 Gap 도출"])

# --- 3. 핵심 유틸리티 함수 ---

def validate_keys():
    if not gemini_key or not serper_key:
        st.error("⚠️ 사이드바에 API 키를 모두 입력해주세요!"); st.stop()

def extract_text(files, url):
    text = ""
    if files:
        for f in files:
            try:
                if f.name.endswith(".pdf"):
                    text += "\n".join([p.extract_text() for p in PdfReader(f).pages])
                elif f.name.endswith(".pptx"):
                    prs = Presentation(f)
                    text += "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
                elif f.name.endswith(".xlsx"):
                    text += pd.read_excel(f).to_string()
            except: text += f"\n[{f.name} 실패]"
    if url:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            for s in soup(['script', 'style']): s.decompose()
            text += f"\n\n[URL]\n{soup.get_text()[:4000]}"
        except: text += "\nhttps://donotfear.tistory.com/93"
    return text

def analyze_ai(content, target_type):
    try:
        client = genai.Client(api_key=gemini_key)
        prompt = f"당신은 15년차 브랜드 전략가입니다. 다음 자료를 심층 분석하여 광고주 보고용 전략 보고서 형태로 상세히 작성하세요.\n\n"
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt + content[:8000])
        return response.text
    except Exception as e: return f"분석 실패: {str(e)}"

def generate_pdf(content_list):
    """가독성을 극대화하고 에러를 방지한 PDF 생성"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # 폰트 경로 확인
    f_reg = "NanumGothic.ttf"
    f_bold = "NanumGothicBold.ttf"
    
    # 확실한 굵기 구분을 위해 별칭으로 등록
    has_fonts = False
    try:
        if os.path.exists(f_reg) and os.path.exists(f_bold):
            pdf.add_font('NG-Reg', '', f_reg)
            pdf.add_font('NG-Bold', '', f_bold)
            has_fonts = True
    except: has_fonts = False

    pdf.add_page()
    
    # [타이틀]
    if has_fonts: pdf.set_font('NG-Bold', size=20)
    else: pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 20, txt="Brand Gap Analysis Strategy Report", ln=True, align='C')
    pdf.ln(10)

    for title, body in content_list:
        if body:
            # [섹션 헤더]
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(0, 51, 102)
            if has_fonts: pdf.set_font('NG-Bold', size=14)
            else: pdf.set_font("Arial", 'B', 12)
            
            # None 출력을 방지하기 위해 단독 실행
            pdf.cell(0, 12, txt=f" {title}", ln=True, fill=True)
            pdf.ln(5)
            
            # [본문]
            pdf.set_text_color(40, 40, 40)
            if has_fonts: pdf.set_font('NG-Reg', size=10.5)
            else: pdf.set_font("Arial", size=10)
            
            # 유니코드 특수문자 정제
            safe_body = body.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u2502', '|')
            pdf.multi_cell(0, 7, txt=safe_body)
            pdf.ln(12)
            
            # 구분선
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
    return bytes(pdf.output())

# --- 4. 메인 로직 ---

if menu == "STEP 1. 브랜드 보이스 분석":
    st.title("🏢 STEP 1. 브랜드 보이스 심층 분석")
    files = st.file_uploader("브랜드 관련 파일", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    url = st.text_input("브랜드 관련 URL")
    if st.button("분석 실행"):
        if not gemini_key: st.error("Gemini Key 입력 필수"); st.stop()
        with st.spinner("분석 중..."):
            raw = extract_text(files, url)
            st.session_state['brand_analysis'] = analyze_ai(raw, "brand")
            st.rerun() # 화면 갱신해서 None 잔상 제거
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 2. 소비자 리얼 보이스 탐색":
    st.title("👥 STEP 2. 소비자 리얼 보이스 분석")
    keywords = st.text_input("검색 키워드 (쉼표 구분)")
    if st.button("데이터 수집 및 분석"):
        validate_keys()
        with st.spinner("탐색 중..."):
            all_res = []
            for kw in [k.strip() for k in keywords.split(",")]:
                try:
                    res = requests.post("https://google.serper.dev/search", 
                                        headers={'X-API-KEY': serper_key, 'Content-Type': 'application/json'}, 
                                        json={"q": f"{kw} 후기", "gl": "kr", "hl": "ko"}).json()
                    if 'organic' in res:
                        for r in res['organic']: all_res.append({'title': r.get('title', ''), 'body': r.get('snippet', '')})
                except: pass
            c_combined = "\n".join([f"{d['title']}: {d['body']}" for d in all_res])
            st.session_state['consumer_analysis'] = analyze_ai(c_combined, "consumer")
            st.rerun()
    if st.session_state['consumer_analysis']: st.markdown(st.session_state['consumer_analysis'])

elif menu == "STEP 3. 전략적 Gap 도출":
    st.title("🧠 STEP 3. 전략 도출 및 다운로드")
    
    if not st.session_state['brand_analysis'] or not st.session_state['consumer_analysis']:
        st.error("이전 단계 분석을 완료해주세요.")
    else:
        if st.button("🚀 최종 전략 리포트 생성"):
            validate_keys()
            with st.spinner("최종 전략 수립 중..."):
                client = genai.Client(api_key=gemini_key)
                prompt = f"광고 전략가로서 아래 데이터를 대조하여 Gap 리포트를 작성하세요.\n\n[브랜드]\n{st.session_state['brand_analysis']}\n\n[소비자]\n{st.session_state['consumer_analysis']}"
                st.session_state['final_report'] = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt).text
                st.rerun()

        if st.session_state['final_report']:
            st.markdown("---")
            st.markdown(st.session_state['final_report'])
            
            st.divider()
            st.subheader("📥 다운로드 설정")
            
            c1, c2, c3 = st.columns(3)
            with c1: inc1 = st.checkbox("브랜드 분석 포함", value=True)
            with c2: inc2 = st.checkbox("소비자 분석 포함", value=True)
            with c3: inc3 = st.checkbox("최종 전략 포함", value=True)
            
            # PDF 생성용 데이터 구성 (화면에 None이 출력되지 않도록 변수에만 저장)
            export_data = []
            if inc1: export_data.append(("BRAND VOICE ANALYSIS", st.session_state['brand_analysis']))
            if inc2: export_data.append(("CONSUMER REAL VOICE", st.session_state['consumer_analysis']))
            if inc3: export_data.append(("STRATEGIC GAP & COPY", st.session_state['final_report']))
            
            if export_data:
                try:
                    # PDF 생성 함수 호출 (화면 출력 없이 바이너리만 가져옴)
                    final_pdf = generate_pdf(export_data)
                    st.download_button(
                        label="📥 통합 리포트 PDF 다운로드 (High Quality)",
                        data=final_pdf,
                        file_name="Total_Strategy_Report.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"PDF 생성 중 오류: {e}")
