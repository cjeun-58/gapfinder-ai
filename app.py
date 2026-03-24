import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io

# --- 1. 기본 설정 및 세션 초기화 ---
st.set_page_config(page_title="GapFinder AI v4.6", layout="wide")

if 'brand_analysis' not in st.session_state: st.session_state['brand_analysis'] = ""
if 'consumer_analysis' not in st.session_state: st.session_state['consumer_analysis'] = ""
if 'final_report' not in st.session_state: st.session_state['final_report'] = ""

# --- 2. 사이드바 ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", ["STEP 1. 브랜드 보이스 분석", "STEP 2. 소비자 리얼 보이스 탐색", "STEP 3. 전략적 Gap 도출"])

# --- 3. 유틸리티 함수 (PDF 생성 포함) ---
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    
    # 한글 폰트 설정 (폰트 파일이 폴더에 있을 경우)
    try:
        # NanumGothic.ttf 파일이 깃허브에 같이 업로드되어 있어야 합니다.
        pdf.add_font('NanumGothic', '', 'NanumGothic.ttf')
        pdf.set_font('NanumGothic', size=12)
    except:
        # 폰트가 없으면 기본 폰트 사용 (한글이 깨질 수 있음)
        pdf.set_font("Arial", size=12)
    
    # 텍스트 줄바꿈 처리 및 작성
    pdf.multi_cell(190, 10, txt=text)
    
    # 메모리상에 PDF 저장
    return pdf.output()

def analyze_content(api_key, content, target_type):
    try:
        client = genai.Client(api_key=api_key)
        role_prompt = "브랜드 전략가로서 내부 자산을 분석하세요." if target_type == "brand" else "소비자 언어와 트렌드를 분석하세요."
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=role_prompt + "\n\n데이터:\n" + content[:6000]
        )
        return response.text
    except: return "분석 중 오류가 발생했습니다."

# --- 4. 메인 로직 ---

# [STEP 1] 브랜드 분석
if menu == "STEP 1. 브랜드 보이스 분석":
    st.title("🏢 브랜드 내부 자산 분석")
    files = st.file_uploader("자료 업로드", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    if st.button("브랜드 분석 시작"):
        if not gemini_key: st.error("Gemini Key를 입력하세요.")
        else:
            with st.spinner("분석 중..."):
                # (텍스트 추출 로직 생략 - 이전 버전과 동일)
                # ... (실제 코드에는 전체 로직 포함됨) ...
                raw_text = "브랜드 데이터 추출 결과..." # 예시
                st.session_state['brand_analysis'] = analyze_content(gemini_key, raw_text, "brand")
                st.success("완료!")
    st.markdown(st.session_state['brand_analysis'])

# [STEP 2] 소비자 탐색 (이전 버전과 동일)
elif menu == "STEP 2. 소비자 리얼 보이스 탐색":
    st.title("👥 소비자 언어 탐색")
    # ... (생략) ...
    st.session_state['consumer_analysis'] = "소비자 분석 결과..." # 예시

# [STEP 3] 전략 도출 및 PDF 다운로드
elif menu == "STEP 3. 전략적 Gap 도출":
    st.title("🧠 최종 전략 리포트 & 다운로드")
    
    if not st.session_state['brand_analysis'] or not st.session_state['consumer_analysis']:
        st.warning("STEP 1, 2 분석을 먼저 완료해주세요.")
    else:
        if st.button("🚀 최종 Gap 분석 실행"):
            with st.spinner("전략 리포트 작성 중..."):
                client = genai.Client(api_key=gemini_key)
                prompt = f"다음 두 분석을 대조하여 광고 전략 보고서를 작성해줘.\n\n[브랜드]\n{st.session_state['brand_analysis']}\n\n[소비자]\n{st.session_state['consumer_analysis']}"
                res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                st.session_state['final_report'] = res.text
        
        if st.session_state['final_report']:
            st.markdown("---")
            st.subheader("📊 전략 리포트 결과")
            st.markdown(st.session_state['final_report'])
            
            # --- PDF 다운로드 섹션 ---
            st.divider()
            pdf_data = create_pdf(st.session_state['final_report'])
            
            st.download_button(
                label="📥 분석 결과 PDF로 다운로드",
                data=pdf_data,
                file_name="Gap_Analysis_Report.pdf",
                mime="application/pdf"
            )
