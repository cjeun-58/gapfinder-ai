import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import time

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="GapFinder AI v3.7", layout="wide")

if 'brand_text' not in st.session_state: st.session_state['brand_text'] = ""
if 'brand_summary' not in st.session_state: st.session_state['brand_summary'] = ""
if 'consumer_data' not in st.session_state: st.session_state['consumer_data'] = []
if 'consumer_summary' not in st.session_state: st.session_state['consumer_summary'] = ""

# --- 2. 사이드바 ---
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

# --- 3. 공통 함수 ---
def validate_api_key():
    if not api_key:
        st.error("⚠️ 사이드바에서 Gemini API Key를 먼저 입력해주세요!")
        st.stop()
    return True

def get_quick_summary(api_key, content, target_type="브랜드"):
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"다음 {target_type} 데이터를 광고 기획용으로 3줄 요약해줘.\n\n" + content[:4000]
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return response.text
    except: return "요약 생성 중 오류가 발생했습니다."

# --- 4. 메인 로직 ---

# [STEP 1] 브랜드 데이터
if menu == "STEP 1. 브랜드 데이터 수집":
    st.title("🏢 STEP 1. 브랜드 데이터 수집")
    files = st.file_uploader("파일 업로드", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    url = st.text_input("브랜드 관련 URL")
    
    if st.button("데이터 저장 및 요약"):
        if validate_api_key():
            with st.spinner("분석 중..."):
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
                st.session_state['brand_summary'] = get_quick_summary(api_key, text, "브랜드")
                st.success("브랜드 데이터 저장 완료!")
    if st.session_state['brand_summary']: st.info(st.session_state['brand_summary'])

# [STEP 2] 소비자 트렌드 (항공사 정보 원천 차단 로직 적용)
elif menu == "STEP 2. 소비자 트렌드 크롤링":
    st.title("👥 STEP 2. 소비자 트렌드 수집")
    keywords = st.text_input("분석 키워드 (쉼표 구분)", placeholder="유리 에어프라이어 후기, 글라스 에어프라이어 단점")
    manual_input = st.text_area("수동 입력 (직접 복사한 내용이 있다면 여기에)")
    
    if st.button("한국어 데이터 수집 시작"):
        if validate_api_key():
            all_results = []
            if keywords:
                kw_list = [k.strip() for k in keywords.split(",")]
                for kw in kw_list:
                    with st.spinner(f"'{kw}' 수집 중..."):
                        try:
                            with DDGS() as ddgs:
                                # [핵심 변경] 검색어에 '사용 후기 단점'을 강제로 붙여서 항공사 정보가 안 나오게 유도
                                # region='kr-kr'을 통해 한국 지역 결과만 고정
                                clean_query = f"{kw} 사용 후기 단점 -항공 -airline"
                                res = list(ddgs.text(clean_query, region='kr-kr', max_results=7))
                                all_results.extend(res)
                            time.sleep(2)
                        except: st.warning(f"'{kw}' 수집 중 일시적 오류가 발생했습니다.")
            
            if manual_input: all_results.append({'title': '직접 입력 데이터', 'body': manual_input})
            
            if not all_results:
                st.error("데이터 수집에 실패했습니다. 키워드를 더 구체적으로 적어주세요.")
            else:
                st.session_state['consumer_data'] = all_results
                combined = "\n".join([f"{r.get('title')}: {r.get('body')}" for r in all_results])
                st.session_state['consumer_summary'] = get_quick_summary(api_key, combined, "소비자")
                st.success(f"{len(all_results)}건 수집 완료!")

    # [원본 데이터 보기 기능 되살리기]
    if st.session_state['consumer_summary']:
        st.info(f"📝 소비자 여론 요약:\n\n{st.session_state['consumer_summary']}")
        st.subheader("🔍 수집된 소비자 원본 데이터 (Raw Data)")
        if st.session_state['consumer_data']:
            df = pd.DataFrame(st.session_state['consumer_data'])
            # 항공사 관련 정보가 섞였는지 확인할 수 있도록 표로 노출
            st.dataframe(df[['title', 'body']], use_container_width=True)

# [STEP 3] 최종 분석
elif menu == "STEP 3. AI 심층 Gap 분석":
    st.title("🧠 STEP 3. AI 심층 Gap 분석")
    if not st.session_state['brand_text'] or not st.session_state['consumer_data']:
        st.error("데이터를 먼저 수집해주세요!")
    else:
        if st.button("🚀 최종 리포트 생성"):
            if validate_api_key():
                with st.spinner("전략 도출 중..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        c_raw = "\n".join([f"{d.get('title')}: {d.get('body')}" for d in st.session_state['consumer_data']])
                        prompt = "광고 전략가로서 아래 데이터를 분석해 브랜드와 소비자의 간극을 분석하고 광고 카피를 제안해줘.\n\n"
                        prompt += f"[브랜드 자료]\n{st.session_state['brand_text'][:6000]}\n\n[소비자 리얼보이스]\n{c_raw[:6000]}"
                        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                        st.markdown("---")
                        st.markdown(res.text)
                    except Exception as e: st.error(f"분석 실패: {e}")
