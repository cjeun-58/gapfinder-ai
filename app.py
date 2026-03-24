import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import time

# --- 1. 설정 ---
st.set_page_config(page_title="GapFinder AI v3.3", layout="wide")

if 'brand_text' not in st.session_state: st.session_state['brand_text'] = ""
if 'brand_summary' not in st.session_state: st.session_state['brand_summary'] = ""
if 'consumer_data' not in st.session_state: st.session_state['consumer_data'] = []
if 'consumer_summary' not in st.session_state: st.session_state['consumer_summary'] = ""

with st.sidebar:
    st.header("🔍 GapFinder AI")
    menu = st.radio("단계별 진행", ["STEP 1. 브랜드 데이터 수집", "STEP 2. 소비자 트렌드 크롤링", "STEP 3. AI 심층 Gap 분석"])
    st.divider()
    api_key = st.text_input("🔑 Gemini API Key 입력", type="password")
    st.subheader("📊 수집 현황")
    b_status = "✅" if st.session_state['brand_text'] else "❌"
    c_status = "✅" if st.session_state['consumer_data'] else "❌"
    st.write(f"브랜드 정보: {b_status}")
    st.write(f"소비자 정보: {c_status} ({len(st.session_state['consumer_data'])}건)")

def validate_api_key():
    if not api_key:
        st.error("⚠️ 사이드바에서 Gemini API Key를 먼저 입력해주세요!")
        st.stop()
    return True

# --- 유틸리티 함수 ---
def extract_text(files, url):
    text = ""
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
    return text

def get_quick_summary(api_key, content, target_type="브랜드"):
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"다음 {target_type} 데이터를 광고 기획용으로 3줄 요약해줘.\n\n" + content[:4000]
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return response.text
    except Exception as e: return f"요약 생성 실패: {str(e)}"

# --- [STEP 1. 브랜드 데이터] ---
if menu == "STEP 1. 브랜드 데이터 수집":
    st.title("🏢 STEP 1. 브랜드 데이터 수집")
    files = st.file_uploader("파일 업로드", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    url = st.text_input("참고 URL")
    if st.button("저장 및 요약"):
        if validate_api_key():
            with st.spinner("분석 중..."):
                st.session_state['brand_text'] = extract_text(files, url)
                st.session_state['brand_summary'] = get_quick_summary(api_key, st.session_state['brand_text'], "브랜드")
                st.success("브랜드 데이터가 저장되었습니다.")
    if st.session_state['brand_summary']: st.info(st.session_state['brand_summary'])

# --- [STEP 2. 소비자 트렌드] ---
elif menu == "STEP 2. 소비자 트렌드 크롤링":
    st.title("👥 STEP 2. 소비자 트렌드 수집")
    st.markdown("자동 크롤링이 안 될 경우, 아래 '수동 입력' 칸에 블로그/리뷰 내용을 직접 복사해 넣어주세요.")
    
    keywords = st.text_input("자동 크롤링 키워드 (쉼표 구분)")
    manual_input = st.text_area("수동 입력 (크롤링 실패 시 직접 복사해서 넣어주세요)")
    
    if st.button("실시간 트렌드 수집 및 요약"):
        if validate_api_key():
            all_results = []
            if keywords:
                kw_list = [k.strip() for k in keywords.split(",")]
                for kw in kw_list:
                    with st.spinner(f"'{kw}' 수집 중..."):
                        try:
                            # 2026년 최신 라이브러리 방식 적용
                            with DDGS() as ddgs:
                                res = list(ddgs.text(kw, max_results=5))
                                if res: all_results.extend(res)
                            time.sleep(2) # 차단 방지를 위해 시간을 늘림
                        except Exception as e:
                            st.warning(f"'{kw}' 자동 수집 실패: {e}")
            
            # 수동 입력 데이터 처리
            if manual_input:
                all_results.append({'title': '수동 입력 데이터', 'body': manual_input})
            
            if not all_results:
                st.error("❌ 수집된 데이터가 0건입니다. 검색어가 너무 길거나 엔진에서 차단했을 수 있습니다. 키워드를 짧게 줄여보거나 '수동 입력'을 이용해주세요.")
            else:
                st.session_state['consumer_data'] = all_results
                combined_c = "\n".join([r.get('title', '') + ": " + r.get('body', '') for r in all_results])
                st.session_state['consumer_summary'] = get_quick_summary(api_key, combined_c, "소비자")
                st.success(f"총 {len(all_results)}건 확보 완료!")

    if st.session_state['consumer_summary']:
        st.info(st.session_state['consumer_summary'])
        with st.expander("원본 데이터"): st.table(pd.DataFrame(st.session_state['consumer_data']))

# --- [STEP 3. 최종 분석] ---
elif menu == "STEP 3. AI 심층 Gap 분석":
    st.title("🧠 STEP 3. 최종 Gap 분석")
    if not st.session_state['brand_text'] or not st.session_state['consumer_data']:
        st.error("데이터를 먼저 수집해주세요!")
    else:
        if st.button("🚀 최종 분석 시작"):
            if validate_api_key():
                with st.spinner("심층 분석 중..."):
                    client = genai.Client(api_key=api_key)
                    c_raw = "\n".join([f"{d.get('title')}: {d.get('body')}" for d in st.session_state['consumer_data']])
                    prompt = "광고 전략가로서 아래 브랜드와 소비자 데이터의 Gap을 분석해줘.\n\n"
                    prompt += "[브랜드]\n" + st.session_state['brand_text'][:6000] + "\n\n[소비자]\n" + c_raw[:6000]
                    res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                    st.markdown("---")
                    st.markdown(res.text)
