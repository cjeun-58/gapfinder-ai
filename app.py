import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# --- 기본 설정 ---
st.set_page_config(page_title="GapFinder AI v2.7", layout="wide")

# 데이터 초기화
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
    try:
        prs = Presentation(file)
        return "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
    except: return "PPT 읽기 실패"

def read_xlsx(file):
    try: return pd.read_excel(file).to_string()
    except: return "엑셀 읽기 실패"

def read_pdf(file):
    try: return "\n".join([page.extract_text() for page in PdfReader(file).pages])
    except: return "PDF 읽기 실패"

def read_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        for s in soup(['script', 'style']): s.decompose()
        return soup.get_text()[:5000]
    except: return "URL 읽기 실패"

# --- [Step 1: 데이터 수집] ---
if page == "Step 1: 데이터 수집":
    st.title("📂 브랜드 & 소비자 데이터 수집")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 브랜드 데이터")
        uploaded_files = st.file_uploader("파일 업로드 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
        brand_url = st.text_input("브랜드 사이트 URL")
        
        if st.button("데이터 통합 저장"):
            combined = ""
            for f in uploaded_files:
                if f.name.endswith(".pdf"): combined += read_pdf(f)
                elif f.name.endswith(".pptx"): combined += read_pptx(f)
                elif f.name.endswith(".xlsx"): combined += read_xlsx(f)
            if brand_url: combined += f"\n\n[웹사이트]\n{read_url(brand_url)}"
            st.session_state['brand_text_combined'] = combined
            st.success("브랜드 데이터 저장 완료!")

    with col2:
        st.subheader("👥 소비자 트렌드")
        keyword = st.text_input("검색어 (예: '무선이어폰 단점')")
        if st.button("실시간 크롤링"):
            with st.spinner("수집 중..."):
                try:
                    with DDGS() as ddgs:
                        st.session_state['consumer_data_list'] = [r for r in ddgs.text(keyword, max_results=10)]
                        st.success("소비자 데이터 수집 완료!")
                except Exception as e: st.error(f"오류: {e}")

    st.divider()
    if st.session_state['brand_text_combined'] or st.session_state['consumer_data_list']:
        st.subheader("📋 수집 현황")
        st.write(f"- 브랜드 데이터: {len(st.session_state['brand_text_combined'])}자 확보")
        st.write(f"- 소비자 데이터: {len(st.session_state['consumer_data_list'])}건 확보")

# --- [Step 2: Gap 분석 리포트] ---
elif page == "Step 2: Gap 분석 리포트":
    st.title("🧠 AI 심층 Gap 분석")
    if not st.session_state['brand_text_combined'] or not st.session_state['consumer_data_list']:
        st.warning("Step 1에서 데이터를 먼저 수집해주세요.")
    else:
        if st.button("🚀 전략 도출 시작"):
            if not api_key: st.error("API Key를 입력하세요.")
            else:
                with st.spinner("분석 중..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        # 에러 방지를 위해 문자열을 아주 안전하게 합칩니다.
                        c_raw = ""
                        for d in st.session_state['consumer_data_list']:
                            c_raw += f"제목: {d['title']}\n내용: {d['body']}\n\n"
                        
                        # 프롬프트 구성 (에러 유발 가능성 차단)
                        instructions = "당신은 광고 대행사 전략가입니다. 브랜드 데이터와 소비자 데이터를 비교해 간극을 분석하고 광고 카피 3개를 제안하세요."
                        final_prompt = instructions + "\n\n[브랜드 데이터]\n" + st.session_state['brand_text_combined'][:7000] + "\n\n[소비자 데이터]\n" + c_raw
                        
                        response = client.models.generate_content(model="gemini-3-flash-preview", contents=final_prompt)
                        st.markdown("---")
                        st.markdown(response.text)
                    except Exception as e: st.error(f"분석 실패: {e}")
