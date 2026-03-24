import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import io
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# --- 설정 ---
st.set_page_config(page_title="GapFinder AI v2.5", layout="wide")

# 세션 데이터 초기화 (페이지 이동 시 데이터 유지)
if 'brand_text_combined' not in st.session_state:
    st.session_state['brand_text_combined'] = ""
if 'consumer_data_list' not in st.session_state:
    st.session_state['consumer_data_list'] = []

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.header("🚀 GapFinder Menu")
    page = st.radio("메뉴 선택", ["Step 1: 데이터 수집 (PPT/엑셀 가능)", "Step 2: Gap 분석 리포트"])
    st.divider()
    api_key = st.text_input("Gemini API Key 입력", type="password")

# --- 파일 읽기 함수들 ---
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

# --- [Step 1: 데이터 수집] ---
if page == "Step 1: 데이터 수집 (PPT/엑셀 가능)":
    st.title("📂 데이터 수집 및 크롤링")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 브랜드 데이터 업로드")
        uploaded_files = st.file_uploader("파일 업로드 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
        
        if st.button("파일 데이터 텍스트 추출 및 저장"):
            combined_text = ""
            for file in uploaded_files:
                if file.name.endswith(".pdf"): combined_text += read_pdf(file)
                elif file.name.endswith(".pptx"): combined_text += read_pptx(file)
                elif file.name.endswith(".xlsx"): combined_text += read_xlsx(file)
            st.session_state['brand_text_combined'] = combined_text
            st.success(f"{len(uploaded_files)}개 파일 추출 완료!")

    with col2:
        st.subheader("👥 소비자 데이터 크롤링")
        keyword = st.text_input("검색 키워드 (예: '비건 샴푸 소비자 반응')")
        if st.button("실시간 웹 크롤링 시작"):
            with st.spinner("수집 중..."):
                with DDGS() as ddgs:
                    results = [r for r in ddgs.text(keyword, max_results=10)]
                    st.session_state['consumer_data_list'] = results
                    st.success(f"'{keyword}' 관련 데이터 10건 수집 완료!")

    # 수집된 현황 보기
    st.divider()
    if st.session_state['consumer_data_list']:
        st.subheader("📋 수집된 소비자 Raw Data (이걸로 분석합니다)")
        st.dataframe(pd.DataFrame(st.session_state['consumer_data_list'])[['title', 'body']], use_container_width=True)

# --- [Step 2: Gap 분석 리포트] ---
elif page == "Step 2: Gap 분석 리포트":
    st.title("🧠 AI Gap 분석 결과")
    
    if not st.session_state['brand_text_combined'] or not st.session_state['consumer_data_list']:
        st.warning("먼저 Step 1에서 데이터를 수집해주세요!")
    else:
        if st.button("🚀 분석 시작"):
            if not api_key:
                st.error("API Key가 필요합니다.")
            else:
                with st.spinner("Gemini 3가 분석 중입니다..."):
                    client = genai.Client(api_key=api_key)
                    consumer_raw = "\n".join([f"제목: {d['title']}\n내용: {d['body']}" for d in st.session_state['consumer_data_list']])
                    
                    prompt = f"""
                    당신은 광고 대행사의 시니어 전략가입니다.
                    [브랜드 데이터]: {st.session_state['brand_text_combined'][:5000]}
                    [소비자 데이터]: {consumer_raw}
                    
                    위 데이터를 바탕으로 브랜드가 주장하는 핵심 가치와 소비자가 실제로 결핍을 느끼는 포인트의 'Gap'을 분석하세요.
                    분석 시 어떤 소비자 데이터(제목 등)를 근거로 했는지 명시하고, 광고 카피 3가지를 제안하세요.
                    """
                    response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                    st.markdown(response.text)
