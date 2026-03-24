import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import time

# --- 1. 기본 설정 및 세션 유지 ---
st.set_page_config(page_title="GapFinder AI v3.1", layout="wide")

if 'brand_text' not in st.session_state: st.session_state['brand_text'] = ""
if 'brand_summary' not in st.session_state: st.session_state['brand_summary'] = ""
if 'consumer_data' not in st.session_state: st.session_state['consumer_data'] = []
if 'consumer_summary' not in st.session_state: st.session_state['consumer_summary'] = ""

# --- 2. 사이드바 내비게이션 ---
with st.sidebar:
    st.header("🔍 GapFinder AI")
    menu = st.radio("단계별 진행", ["STEP 1. 브랜드 데이터 수집", "STEP 2. 소비자 트렌드 크롤링", "STEP 3. AI 심층 Gap 분석"])
    st.divider()
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.subheader("📊 수집 현황")
    b_status = "✅" if st.session_state['brand_text'] else "❌"
    c_status = "✅" if st.session_state['consumer_data'] else "❌"
    st.write(f"브랜드 정보: {b_status}")
    st.write(f"소비자 정보: {c_status}")

# --- 3. 유틸리티 함수 ---
def extract_text(files, url):
    text = ""
    if files:
        for f in files:
            try:
                if f.name.endswith(".pdf"):
                    text += "\n".join([p.extract_text() for p in PdfReader(f).pages])
                elif f.name.endswith(".pptx"):
                    text += "\n".join([s.text for slide in Presentation(f).slides for s in slide.shapes if hasattr(s, "text")])
                elif f.name.endswith(".xlsx"):
                    text += pd.read_excel(f).to_string()
            except: text += f"\n[{f.name} 추출 실패]"
    if url:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            for s in soup(['script', 'style']): s.decompose()
            text += f"\n\nhttps://korean.dict.naver.com/koendict/ko/entry/koen/7d07cd9c14d347e882a66f248420ad10\n{soup.get_text()[:3000]}"
        except: text += "\nhttps://donotfear.tistory.com/93"
    return text

def get_quick_summary(api_key, content, target_type="브랜드"):
    if not api_key or not content: return ""
    try:
        client = genai.Client(api_key=api_key)
        role = "브랜드 데이터" if target_type == "브랜드" else "소비자 리뷰/검색 결과"
        prompt = f"다음은 수집된 {role}입니다. 어떤 내용이 담겨있는지 광고 기획자가 참고하기 좋게 3줄 이내의 불렛포인트 요약(Summary)만 한국어로 작성해주세요.\n\n내용:\n" + content[:4000]
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return response.text
    except: return "요약 생성 실패 (API 키 확인 필요)"

# --- [STEP 1. 브랜드 데이터 수집] ---
if menu == "STEP 1. 브랜드 데이터 수집":
    st.title("🏢 STEP 1. 브랜드 데이터 수집 및 요약")
    files = st.file_uploader("자료 업로드 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    url = st.text_input("브랜드 관련 URL")
    
    if st.button("브랜드 데이터 저장 및 요약"):
        with st.spinner("데이터 분석 중..."):
            raw_text = extract_text(files, url)
            st.session_state['brand_text'] = raw_text
            # 즉석 요약 생성
            summary = get_quick_summary(api_key, raw_text, "브랜드")
            st.session_state['brand_summary'] = summary
            st.success("브랜드 데이터가 저장되었습니다.")

    if st.session_state['brand_summary']:
        st.info("📝 수집 데이터 요약 (Summary)")
        st.markdown(st.session_state['brand_summary'])

# --- [STEP 2. 소비자 트렌드 크롤링] ---
elif menu == "STEP 2. 소비자 트렌드 크롤링":
    st.title("👥 STEP 2. 소비자 트렌드 크롤링 및 테마 분석")
    keywords = st.text_input("분석 키워드 (쉼표로 구분)", placeholder="무선이어폰 단점, 에어팟 프로 후기")
    
    if st.button("실시간 트렌드 수집 및 요약"):
        if not keywords: st.warning("키워드를 입력하세요.")
        else:
            all_results = []
            kw_list = [k.strip() for k in keywords.split(",")]
            for kw in kw_list:
                with st.spinner(f"'{kw}' 수집 중..."):
                    try:
                        with DDGS() as ddgs:
                            res = [r for r in ddgs.text(kw, max_results=5)]
                            all_results.extend(res)
                        time.sleep(1)
                    except: st.error(f"'{kw}' 수집 실패")
            
            st.session_state['consumer_data'] = all_results
            # 소비자 데이터 요약 생성
            combined_c = "\n".join([r['title'] + ": " + r['body'] for r in all_results])
            st.session_state['consumer_summary'] = get_quick_summary(api_key, combined_c, "소비자")
            st.success(f"총 {len(all_results)}건 수집 완료!")

    if st.session_state['consumer_summary']:
        st.info("📝 소비자 여론 요약 (Summary)")
        st.markdown(st.session_state['consumer_summary'])
        with st.expander("원본 데이터 확인 (Raw Data)"):
            st.table(pd.DataFrame(st.session_state['consumer_data'])[['title', 'body']])

# --- [STEP 3. AI 심층 Gap 분석] ---
elif menu == "STEP 3. AI 심층 Gap 분석":
    st.title("🧠 STEP 3. 최종 분석 리포트")
    if not st.session_state['brand_text'] or not st.session_state['consumer_data']:
        st.error("이전 단계에서 데이터를 먼저 수집해주세요!")
    else:
        # 요약본을 미리 보여줘서 신뢰도 상승
        st.subheader("📋 분석 대상 요약")
        c1, c2 = st.columns(2)
        with c1: st.markdown("**[브랜드]**\n" + st.session_state['brand_summary'])
        with c2: st.markdown("**[소비자]**\n" + st.session_state['consumer_summary'])
        
        if st.button("🚀 최종 분석 시작"):
            if not api_key: st.error("API 키를 입력하세요.")
            else:
                with st.spinner("심층 분석 중..."):
                    client = genai.Client(api_key=api_key)
                    c_raw = "\n".join([f"{d['title']}: {d['body']}" for d in st.session_state['consumer_data']])
                    prompt = "당신은 시니어 광고 전략가입니다. 아래 브랜드 데이터와 소비자 데이터를 비교해 간극(Gap)을 분석하고 전략을 제안하세요.\n\n"
                    prompt += "[브랜드]\n" + st.session_state['brand_text'][:6000] + "\n\n[소비자]\n" + c_raw[:6000]
                    
                    response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                    st.markdown("---")
                    st.markdown(response.text)
