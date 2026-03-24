import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
import time

# --- 1. 기본 설정 및 세션 초기화 ---
st.set_page_config(page_title="GapFinder AI v4.5", layout="wide")

if 'brand_text' not in st.session_state: st.session_state['brand_text'] = ""
if 'brand_analysis' not in st.session_state: st.session_state['brand_analysis'] = ""
if 'consumer_data' not in st.session_state: st.session_state['consumer_data'] = []
if 'consumer_analysis' not in st.session_state: st.session_state['consumer_analysis'] = ""

# --- 2. 사이드바 (API 설정 및 메뉴) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", ["STEP 1. 브랜드 보이스 분석", "STEP 2. 소비자 리얼 보이스 탐색", "STEP 3. 전략적 Gap 도출"])
    
    st.subheader("📊 수집 현황")
    st.write(f"브랜드 분석: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"소비자 분석: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 공통 유틸리티 (분석 엔진) ---
def check_keys():
    if not gemini_key or not serper_key:
        st.error("⚠️ 사이드바에 모든 API 키를 입력해주세요!"); st.stop()

def analyze_content(api_key, content, target_type):
    """3줄 요약이 아닌, 전체적인 심층 분석을 수행합니다."""
    try:
        client = genai.Client(api_key=api_key)
        if target_type == "brand":
            prompt = """
            당신은 15년 차 시니어 브랜드 전략가입니다. 아래 제공된 브랜드 자료를 심층 분석하세요.
            1. 브랜드가 지향하는 핵심 가치와 지향점
            2. 현재 커뮤니케이션하고 있는 핵심 소구점(USP) 및 타겟 정의
            3. 브랜드가 주로 사용하는 언어적 특징과 톤앤매너
            내용을 생략하지 말고 전략 기획서의 'Internal Analysis' 섹션처럼 상세하게 서술하세요.
            """
        else:
            prompt = """
            당신은 15년 차 시니어 브랜드 전략가입니다. 아래 제공된 소비자 리얼 보이스(검색 결과)를 심층 분석하세요.
            1. 소비자들이 해당 제품군에서 느끼는 실제 페인 포인트(Pain Point)와 미충족 욕구(Unmet Needs)
            2. 소비자들이 주로 사용하는 리얼 키워드와 맥락
            3. 현재 시장 트렌드와 브랜드에 대한 우호적/부정적 여론 테마
            광고 기획서의 'Consumer & Market Analysis' 섹션처럼 입체적으로 서술하세요.
            """
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt + "\n\n데이터:\n" + content[:6000])
        return response.text
    except: return "분석 생성 실패"

# --- 4. 메인 로직 ---

# [STEP 1] 브랜드 보이스 분석
if menu == "STEP 1. 브랜드 보이스 분석":
    st.title("🏢 STEP 1. 브랜드 내부 자산 분석")
    st.markdown("광고주의 제안서나 상세페이지를 통해 '우리가 하고 싶은 말'을 정의합니다.")
    
    files = st.file_uploader("브랜드 관련 파일 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    url = st.text_input("브랜드 공식 웹사이트 URL")
    
    if st.button("브랜드 보이스 심층 분석"):
        if not gemini_key: st.error("Gemini 키가 필요합니다."); st.stop()
        with st.spinner("브랜드 자산을 분석 중입니다..."):
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
            st.session_state['brand_analysis'] = analyze_content(gemini_key, text, "brand")
            st.success("브랜드 내부 분석이 완료되었습니다.")
    
    if st.session_state['brand_analysis']:
        st.subheader("📊 브랜드 보이스 분석 결과")
        st.markdown(st.session_state['brand_analysis'])

# [STEP 2] 소비자 리얼 보이스 탐색
elif menu == "STEP 2. 소비자 리얼 보이스 탐색":
    st.title("👥 STEP 2. 소비자 언어 및 트렌드 탐색")
    st.markdown("실제 소비자들이 시장에서 사용하는 '리얼 보이스'를 수집하고 분석합니다.")
    kw_input = st.text_input("분석 키워드 (쉼표 구분)", placeholder="유리 에어프라이어 세척, 글라스 에어프라이어 유해물질")
    
    if st.button("소비자 언어 수집 및 분석"):
        check_keys()
        with st.spinner("구글 소셜 데이터를 탐색 중입니다..."):
            all_res = []
            for kw in [k.strip() for k in kw_input.split(",")]:
                try:
                    s_url = "https://google.serper.dev/search"
                    query = f"{kw} (site:naver.com OR site:youtube.com OR site:instagram.com OR site:tistory.com) 후기 리뷰"
                    headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                    res = requests.post(s_url, headers=headers, json={"q": query, "gl": "kr", "hl": "ko"}).json()
                    if 'organic' in res:
                        for r in res['organic']: all_res.append({'title': r.get('title', ''), 'body': r.get('snippet', '')})
                except: pass
            
            st.session_state['consumer_data'] = all_res
            c_text = "\n".join([f"{d['title']}: {d['body']}" for d in all_res])
            st.session_state['consumer_analysis'] = analyze_content(gemini_key, c_text, "consumer")
            st.success(f"{len(all_res)}건의 소비자 목소리를 분석했습니다.")

    if st.session_state['consumer_analysis']:
        st.subheader("📊 소비자 리얼 보이스 분석 결과")
        st.markdown(st.session_state['consumer_analysis'])

# [STEP 3] 전략적 Gap 도출
elif menu == "STEP 3. 전략적 Gap 도출":
    st.title("🧠 STEP 3. 브랜드-소비자 언어 간극 분석 및 전략")
    
    if not st.session_state['brand_analysis'] or not st.session_state['consumer_analysis']:
        st.error("STEP 1과 2의 분석이 완료되어야 합니다.")
    else:
        if st.button("🚀 최종 Gap 분석 및 광고 전략 도출"):
            check_keys()
            with st.spinner("전략적 핵심 간극을 도출하고 있습니다..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    prompt = f"""
                    당신은 국내 최고 광고대행사의 총괄 크리에이티브 디렉터(GCD)입니다.
                    아래 '브랜드 내부 분석'과 '소비자 리얼 보이스 분석'을 대조하여 전략 보고서를 작성하세요.

                    [1단계: 브랜드 내부 분석]
                    {st.session_state['brand_analysis']}

                    [2단계: 소비자 리얼 보이스 분석]
                    {st.session_state['consumer_analysis']}

                    분석 가이드:
                    1. 언어 일치도 분석: 브랜드가 쓰는 용어와 소비자가 찾는 용어가 얼마나 유사한가? (0~100점 점수화)
                    2. 결정적 간극(Gap): 브랜드가 강조하지만 소비자는 관심 없는 것 vs 소비자가 원하지만 브랜드가 말하지 않는 것.
                    3. 전략 방향성(The Way to Go): 소비자 언어로 브랜드를 재정의하기 위한 1줄 핵심 전략.
                    4. 크리에이티브 제안: 소비자 언어와 맥락을 반영한 광고 카피 3가지 및 소재화 아이디어.
                    """
                    res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                    st.markdown("---")
                    st.markdown(res.text)
                except Exception as e: st.error(f"분석 실패: {e}")
