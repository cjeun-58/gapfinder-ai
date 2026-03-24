import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# --- 기본 설정 ---
st.set_page_config(page_title="GapFinder AI v2.6", layout="wide")

# 세션 데이터 초기화 (페이지 이동 시 데이터 보존)
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
    text = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text

def read_xlsx(file):
    df = pd.read_excel(file)
    return df.to_string()

def read_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def read_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        for s in soup(['script', 'style']): s.decompose()
        return soup.get_text()[:5000]
    except Exception as e:
        return f"\nhttps://www.youtube.com/watch?v=HZEKNrUVl9o\n"

# --- [Step 1: 데이터 수집 페이지] ---
if page == "Step 1: 데이터 수집":
    st.title("📂 브랜드 & 소비자 데이터 수집")
    st.info("브랜드 내부 자료와 웹상의 소비자 데이터를 한 곳에 모으세요.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 브랜드 데이터 (내부 자료)")
        uploaded_files = st.file_uploader("파일 업로드 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
        brand_url = st.text_input("브랜드 사이트/상세페이지 URL 입력")
        
        if st.button("모든 브랜드 데이터 통합 저장"):
            with st.spinner("데이터 추출 중..."):
                combined_all_text = ""
                # 파일 처리
                for file in uploaded_files:
                    if file.name.endswith(".pdf"): combined_all_text += read_pdf(file)
                    elif file.name.endswith(".pptx"): combined_all_text += read_pptx(file)
                    elif file.name.endswith(".xlsx"): combined_all_text += read_xlsx(file)
                # URL 처리
                if brand_url:
                    url_text = read_url(brand_url)
                    combined_all_text += f"\n\n[웹사이트 내용]\n{url_text}"
                
                st.session_state['brand_text_combined'] = combined_all_text
                st.success(f"총 {len(uploaded_files)}개의 파일과 웹사이트 데이터가 저장되었습니다!")

    with col2:
        st.subheader("👥 소비자 데이터 (외부 트렌드)")
        keyword = st.text_input("검색 키워드 (예: '무선이어폰 불편한 점')")
        if st.button("실시간 웹 크롤링 시작"):
            if not keyword:
                st.warning("키워드를 입력해주세요.")
            else:
                with st.spinner("수집 중..."):
                    try:
                        with DDGS() as ddgs:
                            results = [r for r in ddgs.text(keyword, max_results=10)]
                            st.session_state['consumer_data_list'] = results
                            st.success(f"'{keyword}' 관련 소비자 데이터 10건 수집 완료!")
                    except Exception as e:
                        st.error(f"크롤링 중 오류 발생: {e}")

    # 데이터 현황 대시보드
    st.divider()
    st.subheader("📋 현재 수집 현황")
    c1, c2 = st.columns(2)
    with c1:
        status = "✅ 수집됨" if st.session_state['brand_text_combined'] else "❌ 미수집"
        st.metric("브랜드 데이터", status)
        if st.session_state['brand_text_combined']:
            with st.expander("브랜드 데이터 미리보기"):
                st.write(st.session_state['brand_text_combined'][:1000] + "...")
    with c2:
        st.metric("소비자 데이터", f"{len(st.session_state['consumer_data_list'])} 건")
        if st.session_state['consumer_data_list']:
            with st.expander("소비자 Raw Data 보기"):
                st.table(pd.DataFrame(st.session_state['consumer_data_list'])[['title', 'body']])

# --- [Step 2: Gap 분석 페이지] ---
elif page == "Step 2: Gap 분석 리포트":
    st.title("🧠 AI 심층 Gap 분석")
    
    if not st.session_state['brand_text_combined'] or not st.session_state['consumer_data_list']:
        st.warning("Step 1에서 데이터를 먼저 수집한 뒤 이동해주세요!")
    else:
        if st.button("🚀 전략 도출 시작"):
            if not api_key:
                st.error("사이드바에 Gemini API Key를 입력해주세요.")
            else:
                with st.spinner("Gemini 3가 분석 리포트를 작성 중입니다..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        consumer_raw = "\n".join([f"- {d['title']}: {d['body']}" for d in st.session_state['consumer_data_list']])
                        
                        prompt = f"""
                        당신은 광고 대행사의 시니어 브랜드 전략가입니다. 아래 데이터를 심층 분석하세요.
