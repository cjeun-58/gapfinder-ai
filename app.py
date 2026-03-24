import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# --- 설정 ---
st.set_page_config(page_title="GapFinder AI v2.6", layout="wide")

# 세션 데이터 초기화
if 'brand_text_combined' not in st.session_state:
    st.session_state['brand_text_combined'] = ""
if 'consumer_data_list' not in st.session_state:
    st.session_state['consumer_data_list'] = []

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.header("🚀 GapFinder Menu")
    page = st.radio("메뉴 선택", ["Step 1: 데이터 수집", "Step 2: Gap 분석 리포트"])
    st.divider()
    api_key = st.text_input("Gemini API Key 입력", type="password")

# --- 데이터 추출 함수들 ---
def read_pptx(file):
    prs = Presentation(file)
    return "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])

def read_xlsx(file):
    return pd.read_excel(file).to_string()

def read_pdf(file):
    return "\n".join([page.extract_text() for page in PdfReader(file).pages])

def read_url(url):
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        # 불필요한 태그 제거 후 텍스트만 추출
        for s in soup(['script', 'style']): s.decompose()
        return soup.get_text()[:5000] # 너무 길면 AI가 힘드니 적당히 자름
    except Exception as e:
        return f"\nhttps://www.korean.go.kr/front/board/boardStandardView.do;front=574EB33611F52111AA90B930096694CF?board_id=7&b_seq=967&mn_id=186\n"

# --- [Step 1: 데이터 수집] ---
if page == "Step 1: 데이터 수집":
    st.title("📂 브랜드 & 소비자 데이터 수집")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 브랜드 데이터 (내부 자료)")
        uploaded_files = st.file_uploader("파일 업로드 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
        brand_url = st.text_input("브랜드 사이트/상세페이지 URL 입력")
        
        if st.button("모든 브랜드 데이터 통합 저장"):
            with st.spinner("파일 및 웹사이트 분석 중..."):
                combined_text = ""
                # 1. 파일 데이터 추출
                for file in uploaded_files:
                    if file.name.endswith(".pdf"): combined_text += read_pdf(file)
                    elif file.name.endswith(".pptx"): combined_text += read_pptx(file)
                    elif file.name.endswith(".xlsx"): combined_text += read_xlsx(file)
                # 2. URL 데이터 추출
                if brand_url:
                    combined_text += f"\n[웹사이트 내용]\n{read_url(brand_
