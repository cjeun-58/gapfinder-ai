import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
import time

# --- 1. 기본 설정 및 세션 초기화 ---
st.set_page_config(page_title="GapFinder AI v4.0", layout="wide")

# 데이터 증발 방지용 세션 기억 장치
for key in ['brand_text', 'brand_summary', 'consumer_data', 'consumer_summary']:
    if key not in st.session_state: st.session_state[key] = "" if 'text' in key or 'summary' in key else []

# --- 2. 사이드바 (모든 열쇠는 여기서 입력) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password", help="serper.dev에서 발급")
    st.divider()
    menu = st.radio("진행 단계", ["STEP 1. 브랜드 분석", "STEP 2. 소비자 탐색", "STEP 3. 전략 도출"])
    
    st.subheader("📊 데이터 상태")
    st.write(f"브랜드: {'✅' if st.session_state['brand_text'] else '❌'}")
    st.write(f"소비자: {'✅' if st.session_state['consumer_data'] else '❌'}")

# --- 3. 공통 유틸리티 ---
def check_keys():
    if not gemini_key or not serper_key:
        st.error("⚠️ 왼쪽 사이드바에 Gemini 키와 Serper 키를 모두 입력해주세요!")
        st.stop()

def get_ai_summary(text, target):
    try:
        client = genai.Client(api_key=gemini_key)
        prompt = f"다음 {target} 데이터를 광고주 보고용으로 3줄 요약해줘.\n\n{text[:4000]}"
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return response.text
    except: return "요약 생성 실패"

# --- 4. 메인 로직 ---

# [STEP 1] 브랜드 데이터 수집
if menu == "STEP 1. 브랜드 분석":
    st.title("🏢 브랜드 데이터 수집")
    files = st.file_uploader("제안서/상세페이지 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    url = st.text_input("브랜드 웹사이트 URL")
    
    if st.button("브랜드 데이터 분석 및 저장"):
        if not gemini_key: st.error("Gemini 키를 먼저 입력하세요!"); st.stop()
        with st.spinner("파일 읽는 중..."):
            text = ""
            if files:
                for f in files:
                    try:
                        if f.name.endswith(".pdf"): text += "\n".join([p.extract_text() for p in PdfReader(f).pages])
                        elif f.name.endswith(".pptx"): text += "\n".join([s.text for slide in Presentation(f).slides for s in slide.shapes if hasattr(s, "text")])
                        elif f.name.endswith(".xlsx"): text += pd.read_excel(f).to_string()
                    except: text += f"\n[{f.name} 실패]"
            if url:
                try:
                    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    for s in soup(['script', 'style']): s.decompose()
                    text += f"\n\n[URL]\n{soup.get_text()[:3000]}"
                except: text += "\nhttps://m.kpedia.jp/w/11817"
            
            st.session_state['brand_text'] = text
            st.session_state['brand_summary'] = get_ai_summary(text, "브랜드 내부 자료")
            st.success("브랜드 분석 완료!")
    
    if st.session_state['brand_summary']: st.info(st.session_state['brand_summary'])

# [STEP 2] 소비자 데이터 크롤링 (Serper API 활용)
elif menu == "STEP 2. 소비자 탐색":
    st.title("👥 고정밀 소비자 트렌드 수집")
    st.caption("구글 검색 기반으로 네이버, 유튜브, 인스타그램 후기를 긁어옵니다.")
    kw_input = st.text_input("분석 키워드 (쉼표 구분)", placeholder="유리 에어프라이어 단점, 에어프라이어 유해물질")
    
    if st.button("실시간 소셜 트렌드 수집"):
        check_keys()
        with st.spinner("구글 엔진 가동 중..."):
            all_res = []
            for kw in [k.strip() for k in kw_input.split(",")]:
                try:
                    # Serper API 호출 (구글 검색 결과)
                    s_url = "https://google.serper.dev/search"
                    # 한국 포털 및 소셜미디어 집중 쿼리
                    query = f"{kw} (site:naver.com OR site:youtube.com OR site:instagram.com OR site:tistory.com) 후기"
                    headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                    res = requests.post(s_url, headers=headers, json={"q": query, "gl": "kr", "hl": "ko"}).json()
                    
                    if 'organic' in res:
                        for r in res['organic']:
                            all_res.append({'title': r.get('title', ''), 'body': r.get('snippet', ''), 'link': r.get('link', '')})
                except: st.warning(f"'{kw}' 수집 중 오류")
            
            st.session_state['consumer_data'] = all_res
            c_text = "\n".join([f"{d['title']}: {d['body']}" for d in all_res])
            st.session_state['consumer_summary'] = get_ai_summary(c_text, "소비자 리얼 보이스")
            st.success(f"총 {len(all_res)}건 수집 완료!")

    if st.session_state['consumer_summary']:
        st.info(st.session_state['consumer_summary'])
        with st.expander("원본 데이터 확인"): st.table(pd.DataFrame(st.session_state['consumer_data']))

# [STEP 3] 최종 Gap 분석
elif menu == "STEP 3. 전략 도출":
    st.title("🧠 AI 심층 Gap 분석 리포트")
    if not st.session_state['brand_text'] or not st.session_state['consumer_data']:
        st.error("STEP 1, 2 데이터를 먼저 수집하세요.")
    else:
        if st.button("🚀 분석 리포트 생성"):
            check_keys()
            with st.spinner("전략 짜는 중..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    c_raw = "\n".join([f"{d['title']}: {d['body']}" for d in st.session_state['consumer_data']])
                    prompt = "광고 기획자로서 아래 데이터를 분석해 Gap 분석과 카피를 제안해줘.\n\n"
                    prompt += f"[브랜드]\n{st.session_state['brand_text'][:6000]}\n\n[소비자]\n{c_raw[:6000]}"
                    res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                    st.markdown("---")
                    st.markdown(res.text)
                except Exception as e: st.error(f"오류: {e}")
