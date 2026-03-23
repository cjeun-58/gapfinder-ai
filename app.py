import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정
st.set_page_config(page_title="GapFinder AI 2026", layout="wide")
st.title("🔍 GapFinder AI (v2.0)")
st.caption("2026 Google Gemini 3 Flash Engine 기반 분석기")

# 2. 사이드바 설정 (API Key 입력)
with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    st.info("💡 API Key는 Google AI Studio에서 무료로 발급 가능합니다.")

# 3. 데이터 입력 섹션
col1, col2 = st.columns(2)

with col1:
    st.header("🏢 브랜드 데이터")
    uploaded_file = st.file_uploader("브랜드 제안서/설명서(PDF) 업로드", type="pdf")
    url_input = st.text_input("브랜드 상세페이지 URL (선택)")

with col2:
    st.header("👥 소비자 데이터")
    search_keyword = st.text_input("분석 키워드 입력 (예: '무선 이어폰 추천')")
    consumer_raw_data = st.text_area("소비자 리뷰/커뮤니티 반응 복사해서 넣기 (선택)")

# --- 데이터 추출 로직 ---
def get_pdf_text(file):
    text = ""
    try:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    except:
        text = "PDF 읽기 실패"
    return text

def get_url_text(url):
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        return soup.get_text()[:2000] # 너무 길면 자름
    except:
        return ""

# 4. 분석 실행
if st.button("🚀 Gap 분석 및 전략 도출"):
    if not api_key:
        st.error("API Key를 먼저 입력해주세요!")
    elif not search_keyword and not uploaded_file:
        st.warning("분석할 데이터를 최소 하나는 입력해주세요.")
    else:
        with st.spinner("Gemini 3가 데이터를 심층 분석 중입니다..."):
            try:
                # 텍스트 수집
                brand_text = ""
                if uploaded_file: brand_text += get_pdf_text(uploaded_file)
                if url_input: brand_text += get_url_text(url_input)
                
                # 2026년형 Gen AI 클라이언트 생성
                client = genai.Client(api_key=api_key)
                
                # 분석 프롬프트 구성
                prompt = f"""
                당신은 광고 대행사의 시니어 브랜드 전략가입니다. 아래 데이터를 분석하여 '간극(Gap) 분석 리포트'를 작성하세요.
                
                [브랜드 제공 정보]: {brand_text[:4000]}
                [소비자 핵심 키워드]: {search_keyword}
                [소비자 리얼 보이스]: {consumer_raw_data[:2000]}
                
                작성 가이드:
                1. '브랜드가 밀고 있는 가치' vs '소비자가 진짜 원하는 니즈'를 5:5로 대조하세요.
                2. 두 영역의 간극을 0~100점 점수로 표현하고 이유를 짧게 쓰세요.
                3. DA 광고 배너에 바로 쓸 수 있는 '수정된 메시지(Copy)' 3가지를 제안하세요.
                4. 모든 내용은 한국어로, 광고주 보고용으로 격식 있게 작성하세요.
                """
                
                # Gemini 3 Flash 모델 호출 (2026년 최신 모델명)
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=prompt
                )
                
                # 결과 출력
                st.markdown("---")
                st.subheader("📊 분석 결과 리포트")
                st.markdown(response.text)
                st.success("분석이 완료되었습니다!")
                
            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {e}")
                st.info("팁: 모델명이나 API Key 권한을 다시 확인해 보세요.")
