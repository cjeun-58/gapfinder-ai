import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# --- 기본 설정 ---
st.set_page_config(page_title="GapFinder AI v2.0", layout="wide")

# 세션 상태 초기화 (페이지 간 데이터 공유를 위해 필요)
if 'brand_data' not in st.session_state:
    st.session_state['brand_data'] = []
if 'consumer_data' not in st.session_state:
    st.session_state['consumer_data'] = []
if 'analysis_result' not in st.session_state:
    st.session_state['analysis_result'] = None

# --- 사이드바 메뉴 (페이지 이동) ---
with st.sidebar:
    st.header("🚀 GapFinder Menu")
    page = st.radio("이동할 페이지 선택", ["Step 1: 데이터 수집 & 크롤링", "Step 2: Gap 분석 & 인사이트"])
    st.divider()
    api_key = st.text_input("Gemini API Key", type="password")
    st.info("2026 Gemini 3 Flash 엔진 사용")

# --- 유틸리티 함수 (크롤링 및 추출) ---
def crawl_search_results(query):
    """구글/네이버 대신 DuckDuckGo를 통해 무료로 검색 결과를 긁어옵니다."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=10):
            results.append({"title": r['title'], "snippet": r['body'], "link": r['href']})
    return results

def extract_pdf_text(files):
    all_text = ""
    for file in files:
        reader = PdfReader(file)
        for page in reader.pages:
            all_text += page.extract_text() + "\n"
    return all_text

# --- [페이지 1: 데이터 수집 & 크롤링] ---
if page == "Step 1: 데이터 수집 & 크롤링":
    st.title("📂 Step 1: 데이터 수집 및 자동 크롤링")
    st.markdown("브랜드 자료를 업로드하고, 소비자 트렌드를 실시간으로 크롤링하세요.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 브랜드 데이터 (다중 업로드)")
        files = st.file_uploader("제안서, 상세페이지 PDF (여러 개 가능)", type="pdf", accept_multiple_files=True)
        brand_url = st.text_input("공식 홈페이지/상세페이지 URL")
        
        if st.button("브랜드 데이터 저장"):
            text = extract_pdf_text(files) if files else ""
            st.session_state['brand_data'] = text
            st.success(f"{len(files)}개의 파일이 저장되었습니다.")

    with col2:
        st.subheader("👥 소비자 데이터 (자동 크롤링)")
        keyword = st.text_input("검색 키워드 (예: '20대 무선 이어폰 트렌드', '브랜드명 후기')")
        
        if st.button("실시간 크롤링 시작"):
            if keyword:
                with st.spinner("검색 결과를 수집 중입니다..."):
                    search_results = crawl_search_results(keyword)
                    st.session_state['consumer_data'] = search_results
                    st.success(f"'{keyword}'에 대한 {len(search_results)}개의 데이터를 수집했습니다.")
            else:
                st.warning("키워드를 입력해주세요.")

    # 수집 현황 확인 (Raw Data 미리보기)
    st.divider()
    st.subheader("📋 현재 수집된 Raw Data 요약")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**브랜드 데이터:**", "데이터 있음" if st.session_state['brand_data'] else "비어 있음")
    with c2:
        if st.session_state['consumer_data']:
            df = pd.DataFrame(st.session_state['consumer_data'])
            st.dataframe(df[['title', 'snippet']], use_container_width=True)
        else:
            st.write("**소비자 데이터:** 비어 있음")

# --- [페이지 2: Gap 분석 & 인사이트] ---
elif page == "Step 2: Gap 분석 & 인사이트":
    st.title("🧠 Step 2: AI Gap 분석 및 전략 도출")
    
    if not st.session_state['brand_data'] or not st.session_state['consumer_data']:
        st.error("Step 1에서 데이터를 먼저 수집해주세요!")
    else:
        if st.button("🚀 전체 데이터 분석 시작"):
            if not api_key:
                st.error("API Key를 입력해주세요.")
            else:
                with st.spinner("Gemini 3가 방대한 데이터를 비교 분석 중입니다..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        
                        # 컨텍스트 구성
                        consumer_raw = "\n".join([f"제목: {d['title']}\n내용: {d['snippet']}" for d in st.session_state['consumer_data']])
                        
                        prompt = f"""
                        당신은 광고 대행사 전략팀장입니다. 아래 수집된 '브랜드 데이터'와 '실시간 소비자 크롤링 데이터'를 비교 분석하세요.
                        
                        [브랜드 내부 데이터]: {st.session_state['brand_data'][:5000]}
                        [소비자 실시간 데이터]: {consumer_raw}
                        
                        요청 사항:
                        1. 브랜드가 고집하는 언어 vs 소비자가 실제로 쓰는 언어를 3가지 세트로 대조해라.
                        2. 소비자의 결핍(Unmet Needs)을 데이터 근거와 함께 제시해라.
                        3. 현재 캠페인 메시지를 어떻게 수정해야 하는지 구체적인 A/B 테스트 안을 제안해라.
                        4. 갭 점수를 산출하고, 이 결과가 나온 근거가 된 소비자 데이터를 언급해라.
                        """
                        
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            contents=prompt
                        )
                        st.session_state['analysis_result'] = response.text
                    except Exception as e:
                        st.error(f"오류 발생: {e}")

        # 분석 결과 출력 (탭 구성)
        if st.session_state['analysis_result']:
            tab1, tab2 = st.tabs(["📊 전략 리포트", "🔍 분석 근거 (Raw Data)"])
            
            with tab1:
                st.markdown(st.session_state['analysis_result'])
            
            with tab2:
                st.write("AI가 분석에 참고한 원본 데이터 리스트입니다.")
                df_raw = pd.DataFrame(st.session_state['consumer_data'])
                st.table(df_raw)
