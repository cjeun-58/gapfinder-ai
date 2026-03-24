import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import time
import io

# --- 1. 기본 설정 및 세션 초기화 ---
st.set_page_config(page_title="GapFinder AI v4.7", layout="wide")

# 데이터 휘발 방지용 세션 상태 설정
if 'brand_text' not in st.session_state: st.session_state['brand_text'] = ""
if 'brand_analysis' not in st.session_state: st.session_state['brand_analysis'] = ""
if 'consumer_data' not in st.session_state: st.session_state['consumer_data'] = []
if 'consumer_analysis' not in st.session_state: st.session_state['consumer_analysis'] = ""
if 'final_report' not in st.session_state: st.session_state['final_report'] = ""

# --- 2. 사이드바 설정 ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", ["STEP 1. 브랜드 보이스 분석", "STEP 2. 소비자 리얼 보이스 탐색", "STEP 3. 전략적 Gap 도출"])
    
    st.subheader("📊 수집 현황")
    b_status = "✅" if st.session_state['brand_analysis'] else "❌"
    c_status = "✅" if st.session_state['consumer_analysis'] else "❌"
    st.write(f"브랜드 분석: {b_status}")
    st.write(f"소비자 분석: {c_status}")

# --- 3. 핵심 유틸리티 함수 ---

def validate_keys():
    if not gemini_key or not serper_key:
        st.error("⚠️ 사이드바에 Gemini 및 Serper API 키를 모두 입력해주세요!")
        st.stop()

def extract_brand_data(files, url):
    """파일과 URL에서 텍스트를 추출합니다."""
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
            text += f"\n\n[웹사이트 내용]\n{soup.get_text()[:3000]}"
        except: text += "\nhttps://donotfear.tistory.com/93"
    return text

def analyze_ai(content, target_type):
    """Gemini를 이용해 심층 분석을 수행합니다."""
    try:
        client = genai.Client(api_key=gemini_key)
        if target_type == "brand":
            prompt = "당신은 시니어 브랜드 전략가입니다. 아래 브랜드 자료의 핵심 가치, USP, 사용 언어를 심층 분석하세요.\n\n"
        else:
            prompt = "당신은 시니어 브랜드 전략가입니다. 아래 소비자 데이터에서 페인포인트, 미충족 욕구, 리얼 키워드를 추출하세요.\n\n"
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt + content[:7000])
        return response.text
    except: return "분석 실패"

def generate_pdf(report_text):
    """한글 폰트 대응 및 PDF 생성"""
    pdf = FPDF()
    pdf.add_page()
    try:
        # NanumGothic.ttf 파일이 깃허브 상위 폴더에 있어야 합니다.
        pdf.add_font('NanumGothic', '', 'NanumGothic.ttf')
        pdf.set_font('NanumGothic', size=11)
    except:
        pdf.set_font("Arial", size=10)
    
    # PDF 내용 작성 (멀티 셀로 자동 줄바꿈)
    pdf.multi_cell(0, 8, txt=report_text)
    return pdf.output()

# --- 4. 메인 로직 ---

# [STEP 1. 브랜드 분석]
if menu == "STEP 1. 브랜드 보이스 분석":
    st.title("🏢 브랜드 내부 자산 심층 분석")
    st.markdown("제안서 파일과 공식 사이트 URL을 통해 우리 브랜드의 현재 목소리를 진단합니다.")
    
    brand_files = st.file_uploader("브랜드 관련 파일 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    brand_url = st.text_input("브랜드 공식 웹사이트/상세페이지 URL")
    
    if st.button("브랜드 데이터 분석 시작"):
        if not gemini_key: st.error("Gemini Key를 먼저 입력하세요!"); st.stop()
        with st.spinner("브랜드 자산을 심층 분석 중..."):
            raw_text = extract_brand_data(brand_files, brand_url)
            st.session_state['brand_text'] = raw_text
            st.session_state['brand_analysis'] = analyze_ai(raw_text, "brand")
            st.success("브랜드 내부 분석이 완료되었습니다!")

    if st.session_state['brand_analysis']:
        st.subheader("📊 브랜드 보이스 분석 결과")
        st.markdown(st.session_state['brand_analysis'])

# [STEP 2. 소비자 탐색]
elif menu == "STEP 2. 소비자 리얼 보이스 탐색":
    st.title("👥 소비자 언어 및 트렌드 수집")
    st.markdown("Serper API를 통해 소셜(네이버, 유튜브, 인스타 등)의 리얼 보이스를 긁어옵니다.")
    keywords = st.text_input("분석 키워드 (쉼표 구분)", placeholder="유리 에어프라이어 세척, 에어프라이어 유해물질")
    
    if st.button("소비자 데이터 수집 및 분석"):
        validate_keys()
        with st.spinner("구글 검색 엔진 가동 및 여론 분석 중..."):
            all_res = []
            for kw in [k.strip() for k in keywords.split(",")]:
                try:
                    s_url = "https://google.serper.dev/search"
                    q = f"{kw} (site:naver.com OR site:youtube.com OR site:instagram.com) 후기 리뷰"
                    headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                    res = requests.post(s_url, headers=headers, json={"q": q, "gl": "kr", "hl": "ko"}).json()
                    if 'organic' in res:
                        for r in res['organic']: all_res.append({'title': r.get('title', ''), 'body': r.get('snippet', '')})
                except: pass
            
            st.session_state['consumer_data'] = all_res
            c_combined = "\n".join([f"{d['title']}: {d['body']}" for d in all_res])
            st.session_state['consumer_analysis'] = analyze_ai(c_combined, "consumer")
            st.success(f"총 {len(all_res)}건의 데이터를 기반으로 소비자 언어를 분석했습니다.")

    if st.session_state['consumer_analysis']:
        st.subheader("📊 소비자 리얼 보이스 분석 결과")
        st.markdown(st.session_state['consumer_analysis'])

# [STEP 3. 전략적 Gap 도출]
elif menu == "STEP 3. 전략적 Gap 도출":
    st.title("🧠 최종 Gap 분석 및 광고 전략")
    if not st.session_state['brand_analysis'] or not st.session_state['consumer_analysis']:
        st.error("STEP 1과 2의 분석이 먼저 선행되어야 합니다.")
    else:
        if st.button("🚀 최종 분석 리포트 생성"):
            validate_keys()
            with st.spinner("브랜드와 소비자의 간극을 분석 중..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    prompt = f"""
                    당신은 15년 차 광고 전략가입니다. 아래 두 분석 결과를 대조하여 'Gap 분석 리포트'를 작성하세요.
                    
                    [브랜드 내부 분석]
                    {st.session_state['brand_analysis']}
                    
                    [소비자 리얼 보이스 분석]
                    {st.session_state['consumer_analysis']}
                    
                    요청 사항:
                    1. 언어 일치도 점수 및 근거
                    2. 브랜드 중심 언어 vs 소비자 중심 언어의 결정적 차이(Gap)
                    3. 소비자의 결핍을 건드리는 1줄 핵심 전략 방향
                    4. 리얼 보이스를 활용한 광고 카피 3선 및 크리에이티브 가이드
                    """
                    res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                    st.session_state['final_report'] = res.text
                except Exception as e: st.error(f"리포트 생성 실패: {e}")

        if st.session_state['final_report']:
            st.markdown("---")
            st.subheader("📊 전략 리포트 결과")
            st.markdown(st.session_state['final_report'])
            
            # PDF 다운로드 버튼
            st.divider()
            pdf_bytes = generate_pdf(st.session_state['final_report'])
            st.download_button(
                label="📥 분석 결과 PDF 다운로드",
                data=pdf_bytes,
                file_name="Brand_Gap_Strategy_Report.pdf",
                mime="application/pdf"
            )
