import streamlit as st
import google.generativeai as genai
import pandas as pd
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="GapFinder AI", layout="wide")
st.title("🔍 GapFinder AI")
st.subheader("브랜드가 밀고 싶은 말 vs 소비자가 듣고 싶은 말의 간극 분석")

# 2. API 키 입력 (사이드바)
with st.sidebar:
    st.header("설정")
    api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    if api_key:
        genai.configure(api_key=api_key)

# 3. 데이터 입력 섹션
col1, col2 = st.columns(2)

with col1:
    st.header("🏢 브랜드 데이터")
    uploaded_file = st.file_uploader("브랜드 제안서/상세설명서(PDF) 업로드", type="pdf")
    url_input = st.text_input("상세페이지 URL 입력 (선택사항)")

with col2:
    st.header("👥 소비자 데이터")
    search_keyword = st.text_input("분석할 키워드를 입력하세요 (예: 무선 이어폰 추천)")
    consumer_raw_data = st.text_area("추가 소비자 의견 (블로그/리뷰 내용 복붙 가능 - 선택사항)")

# 데이터 추출 함수들
def extract_pdf_text(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_url_text(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        return soup.get_text()
    except:
        return ""

# 4. 분석 시작 버튼
if st.button("🚀 Gap 분석 시작"):
    if not api_key:
        st.error("API Key를 입력해주세요!")
    else:
        with st.spinner("AI가 데이터를 분석 중입니다... 잠시만 기다려주세요."):
            # 브랜드 텍스트 수집
            brand_text = ""
            if uploaded_file:
                brand_text += extract_pdf_text(uploaded_file)
            if url_input:
                brand_text += extract_url_text(url_input)
            
            # AI에게 보낼 프롬프트 구성
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            당신은 10년차 베테랑 광고 전략가입니다. 아래 데이터를 바탕으로 Gap 분석을 수행하세요.
            
            [브랜드 데이터]: {brand_text[:3000]} 
            [소비자 키워드]: {search_keyword}
            [소비자 추가 데이터]: {consumer_raw_data}

            분석 내용:
            1. 브랜드가 강조하는 핵심 키워드 5개 추출
            2. 소비자가 해당 제품군에서 실제로 가장 궁금해하거나 해결하고 싶어하는 니즈 5개 추출
            3. 브랜드 언어와 소비자 언어의 간극 점수 (0~100점)
            4. 광고 메시지 개선 제안 (표 형식)
            
            출력 형식: 반드시 한국어로 작성하고, 시각적으로 보기 편하게 마크다운 형식을 사용하세요.
            """
            
            response = model.generate_content(prompt)
            
            # 결과 화면 출력
            st.divider()
            st.markdown(response.text)
            st.success("분석이 완료되었습니다!")
