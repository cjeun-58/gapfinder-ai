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
st.set_page_config(page_title="GapFinder AI v6.0", layout="wide")

# 세션 데이터 초기화
for key in ['brand_text', 'brand_analysis', 'consumer_data', 'consumer_analysis', 'final_report']:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key else []

# --- 2. 사이드바 (상태 체크 및 메뉴) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    
    # 메뉴 선택
    menu = st.radio("전략 수립 단계", ["STEP 1. 브랜드 보이스 분석", "STEP 2. 소비자 리얼 보이스 탐색", "STEP 3. 전략적 Gap 도출"])
    st.divider()

    # [수정] 수집 현황 체크박스 (항상 보이도록 상단 배치)
    st.subheader("📊 실시간 분석 현황")
    b_check = "✅ 완료" if st.session_state['brand_analysis'] else "❌ 미완료"
    c_check = "✅ 완료" if st.session_state['consumer_analysis'] else "❌ 미완료"
    st.write(f"🏢 브랜드 분석: {b_check}")
    st.write(f"👥 소비자 분석: {c_check}")

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
            text += f"\n\n[웹사이트 내용]\n{soup.get_text()[:4000]}"
        except: text += "\nhttps://donotfear.tistory.com/93"
    return text

def analyze_ai(content, target_type):
    try:
        client = genai.Client(api_key=gemini_key)
        # [수정] 자기소개 금지 프롬프트 추가
        intro_skip = "본인에 대한 자기소개나 인사(예: 15년차 전략가입니다 등)는 일절 생략하고 바로 분석 내용부터 작성하세요."
        if target_type == "brand":
            prompt = f"{intro_skip}\n제공된 브랜드 자료의 핵심 가치, USP, 사용 언어를 심층 분석하여 광고주 보고용 전략 문서 형태로 작성하세요."
        else:
            prompt = f"{intro_skip}\n제공된 소비자 데이터에서 페인포인트, 미충족 욕구, 실제 언어 맥락을 분석하여 시장 분석 리포트 형태로 작성하세요."
        
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt + "\n\n데이터:\n" + content[:8000])
        return response.text
    except Exception as e: return f"분석 실패: {str(e)}"

def generate_pdf(content_list):
    """가독성을 극대화하고 볼드체를 적용한 PDF 생성"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    f_reg = "NanumGothic.ttf"
    f_bold = "NanumGothicBold.ttf"
    
    # [수정] 동일 패밀리 네임으로 스타일 구분 등록
    try:
        if os.path.exists(f_reg) and os.path.exists(f_bold):
            pdf.add_font('NanumGothic', '', f_reg)
            pdf.add_font('NanumGothic', 'B', f_bold)
            pdf.set_font('NanumGothic', size=11)
            use_fonts = True
        else: use_fonts = False
    except: use_fonts = False

    pdf.add_page()
    
    # 타이틀
    if use_fonts: pdf.set_font('NanumGothic', 'B', 20)
    else: pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 20, txt="Brand Gap Analysis Strategy Report", ln=True, align='C')
    pdf.ln(10)

    for title, body in content_list:
        if body:
            # 섹션 제목 (굵게)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(0, 51, 102)
            if use_fonts: pdf.set_font('NanumGothic', 'B', 14)
            else: pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 12, txt=f" {title}", ln=True, fill=True)
            pdf.ln(5)
            
            # 본문 (일반)
            pdf.set_text_color(40, 40, 40)
            if use_fonts: pdf.set_font('NanumGothic', '', 10.5)
            else: pdf.set_font("Arial", size=10)
            
            safe_body = body.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-')
            pdf.multi_cell(0, 8, txt=safe_body)
            pdf.ln(10)
            
    # 바이너리 변환 시 "None" 출력을 방지
    pdf_out = pdf.output()
    return bytes(pdf_out)

# --- 4. 메인 로직 ---

if menu == "STEP 1. 브랜드 보이스 분석":
    st.title("🏢 STEP 1. 브랜드 보이스 분석")
    files = st.file_uploader("파일 업로드 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    url = st.text_input("브랜드 웹사이트/상세페이지 URL")
    if st.button("브랜드 분석 실행"):
        if not gemini_key: st.error("Gemini Key가 필요합니다."); st.stop()
        with st.spinner("브랜드 데이터를 분석 중입니다..."):
            raw = extract_text(files, url)
            st.session_state['brand_text'] = raw
            st.session_state['brand_analysis'] = analyze_ai(raw, "brand")
            st.rerun() # 상태 업데이트를 위해 화면 재설정
    if st.session_state['brand_analysis']:
        st.subheader("📊 브랜드 분석 리포트")
        st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 2. 소비자 리얼 보이스 탐색":
    st.title("👥 STEP 2. 소비자 트렌드 분석")
    keywords = st.text_input("분석 키워드 (쉼표 구분)")
    if st.button("데이터 수집 및 분석"):
        validate_keys()
        with st.spinner("소비자 언어를 탐색 중입니다..."):
            all_res = []
            for kw in [k.strip() for k in keywords.split(",")]:
                try:
                    res = requests.post("https://google.serper.dev/search", 
                                        headers={'X-API-KEY': serper_key, 'Content-Type': 'application/json'}, 
                                        json={"q": f"{kw} 후기 리뷰", "gl": "kr", "hl": "ko"}).json()
                    if 'organic' in res:
                        for r in res['organic']: all_res.append({'title': r.get('title', ''), 'body': r.get('snippet', '')})
                except: pass
            c_combined = "\n".join([f"{d['title']}: {d['body']}" for d in all_res])
            st.session_state['consumer_analysis'] = analyze_ai(c_combined, "consumer")
            st.rerun()
    if st.session_state['consumer_analysis']:
        st.subheader("📊 소비자 트렌드 분석 리포트")
        st.markdown(st.session_state['consumer_analysis'])

elif menu == "STEP 3. 전략적 Gap 도출":
    st.title("🧠 STEP 3. 전략 도출 및 통합 리포트")
    if not st.session_state['brand_analysis'] or not st.session_state['consumer_analysis']:
        st.warning("STEP 1과 2의 분석이 먼저 완료되어야 합니다.")
    else:
        if st.button("🚀 최종 전략 리포트 생성"):
            validate_keys()
            with st.spinner("브랜드와 소비자의 간극을 분석 중..."):
                client = genai.Client(api_key=gemini_key)
                # [수정] 자기소개 금지 가이드
                prompt = "자기소개 없이 바로 본론부터 작성해라. 브랜드 자료와 소비자 데이터를 비교하여 광고 전략 보고서를 작성해라.\n\n"
                prompt += f"[브랜드]\n{st.session_state['brand_analysis']}\n\n[소비자]\n{st.session_state['consumer_analysis']}"
                st.session_state['final_report'] = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt).text
                st.rerun()

        if st.session_state['final_report']:
            st.markdown("---")
            st.markdown(st.session_state['final_report'])
            
            st.divider()
            st.subheader("📥 리포트 통합 다운로드")
            col1, col2, col3 = st.columns(3)
            with col1: i1 = st.checkbox("브랜드 분석 포함", value=True)
            with col2: i2 = st.checkbox("소비자 분석 포함", value=True)
            with col3: i3 = st.checkbox("최종 전략 포함", value=True)
            
            export_list = []
            if i1: export_list.append(("BRAND VOICE ANALYSIS", st.session_state['brand_analysis']))
            if i2: export_list.append(("CONSUMER REAL VOICE", st.session_state['consumer_analysis']))
            if i3: export_list.append(("FINAL GAP STRATEGY", st.session_state['final_report']))
            
            if export_list:
                try:
                    pdf_data = generate_pdf(export_list)
                    st.download_button(label="📥 통합 PDF 다운로드", data=pdf_data, file_name="Strategy_Report.pdf", mime="application/pdf")
                except: st.error("PDF 생성 중 오류가 발생했습니다.")
