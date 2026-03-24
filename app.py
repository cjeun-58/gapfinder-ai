import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io
import time
import os

# --- 1. 기본 설정 및 데이터 초기화 ---
st.set_page_config(page_title="GapFinder AI v6.5", layout="wide")

# 세션 데이터 초기화 (경쟁사 분석 필드 추가)
states = ['brand_text', 'brand_analysis', 'comp_text', 'comp_analysis', 
          'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key else []

# --- 2. 사이드바 (API 설정 및 단계 확장) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 브랜드 보이스 분석", 
        "STEP 1.5. 경쟁사 보이스 분석", # 신설
        "STEP 2. 소비자 리얼 보이스 탐색", 
        "STEP 3. 전략적 Gap 도출"
    ])
    st.divider()

    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 브랜드: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 핵심 유틸리티 함수 ---

def validate_keys():
    if not gemini_key or not serper_key:
        st.error("⚠️ API 키를 입력해주세요!"); st.stop()

def extract_text(files, url):
    text = ""
    if files:
        for f in files:
            try:
                if f.name.endswith(".pdf"): text += "\n".join([p.extract_text() for p in PdfReader(f).pages])
                elif f.name.endswith(".pptx"):
                    prs = Presentation(f)
                    text += "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
                elif f.name.endswith(".xlsx"): text += pd.read_excel(f).to_string()
            except: pass
    if url:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            for s in soup(['script', 'style']): s.decompose()
            text += f"\n\nhttps://korean.dict.naver.com/koendict/ko/entry/koen/7d07cd9c14d347e882a66f248420ad10\n{soup.get_text()[:4000]}"
        except: pass
    return text

def analyze_ai(content, target_type):
    try:
        client = genai.Client(api_key=gemini_key)
        # 자기소개 제외 및 분석 고도화 프롬프트
        prompts = {
            "brand": "자기소개 없이, 제공된 브랜드 자료의 핵심 가치, USP, 사용 언어 스타일을 광고 기획서의 '자사 분석' 수준으로 상세히 분석하세요.",
            "comp": "자기소개 없이, 경쟁사의 제품 소구점, 마케팅 워딩, 강조하는 성분 및 이미지를 분석하여 '경쟁사 분석' 리포트 형태로 작성하세요.",
            "consumer": "자기소개 없이, 소비자 데이터에서 반복되는 페인포인트, 상황별 맥락(Occasion), 그들이 사용하는 날것의 언어를 분석하세요."
        }
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[target_type] + "\n\n데이터:\n" + content[:8000])
        return response.text
    except Exception as e: return f"분석 실패: {str(e)}"

def generate_pdf(content_list):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
    try:
        pdf.add_font('NG', '', f_reg); pdf.add_font('NG', 'B', f_bold)
        pdf.set_font('NG', size=11); use_f = True
    except: pdf.set_font("Arial", size=10); use_f = False

    pdf.add_page()
    pdf.set_font('NG', 'B', 20) if use_f else pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 20, txt="Brand Strategy & Gap Analysis Report", ln=True, align='C')

    for title, body in content_list:
        if body:
            pdf.set_fill_color(240, 240, 240); pdf.set_font('NG', 'B', 14) if use_f else pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 12, txt=f" {title}", ln=True, fill=True)
            pdf.ln(5); pdf.set_font('NG', '', 10.5) if use_f else pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 8, txt=body.replace('\u2022', '-').encode('utf-8', 'ignore').decode('utf-8'))
            pdf.ln(10)
    return bytes(pdf.output())

# --- 4. 메인 로직 ---

# [STEP 1] 자사 분석
if menu == "STEP 1. 브랜드 보이스 분석":
    st.title("🏢 STEP 1. 자사 브랜드 보이스 분석")
    files = st.file_uploader("자사 자료 업로드", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    url = st.text_input("자사 사이트/상세페이지 URL")
    if st.button("자사 분석 실행"):
        with st.spinner("분석 중..."):
            st.session_state['brand_analysis'] = analyze_ai(extract_text(files, url), "brand")
            st.rerun()
    st.markdown(st.session_state['brand_analysis'])

# [STEP 1.5] 경쟁사 분석 (신설)
elif menu == "STEP 1.5. 경쟁사 보이스 분석":
    st.title("⚔️ STEP 1.5. 경쟁사 커뮤니케이션 분석")
    st.info("비교하고 싶은 경쟁 브랜드의 사이트나 분석 자료를 넣어주세요.")
    c_files = st.file_uploader("경쟁사 자료 업로드", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    c_url = st.text_input("경쟁사 사이트/상세페이지 URL")
    if st.button("경쟁사 분석 실행"):
        with st.spinner("경쟁사 전략 파악 중..."):
            st.session_state['comp_analysis'] = analyze_ai(extract_text(c_files, c_url), "comp")
            st.rerun()
    st.markdown(st.session_state['comp_analysis'])

# [STEP 2] 소비자 탐색 (제외 키워드 및 원본 보기 추가)
elif menu == "STEP 2. 소비자 리얼 보이스 탐색":
    st.title("👥 STEP 2. 소비자 언어 및 트렌드 분석")
    keywords = st.text_input("포함 키워드 (쉼표 구분)")
    exclude = st.text_input("제외 키워드 (쉼표 구분)", help="검색 결과에서 빼고 싶은 단어 (예: 항공, 일본)")
    if st.button("소비자 데이터 수집"):
        validate_keys()
        with st.spinner("소셜 보이스 수집 중..."):
            all_res = []
            ex_query = " ".join([f"-{x.strip()}" for x in exclude.split(",") if x.strip()])
            for kw in [k.strip() for k in keywords.split(",")]:
                q = f"{kw} {ex_query} (site:naver.com OR site:youtube.com OR site:instagram.com) 후기"
                res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, 
                                    json={"q": q, "gl": "kr", "hl": "ko"}).json()
                if 'organic' in res: all_res.extend([{'title': r.get('title', ''), 'body': r.get('snippet', '')} for r in res['organic']])
            st.session_state['consumer_data'] = all_res
            st.session_state['consumer_analysis'] = analyze_ai("\n".join([f"{d['title']}: {d['body']}" for d in all_res]), "consumer")
            st.rerun()
    
    if st.session_state['consumer_analysis']:
        st.subheader("📊 소비자 분석 리포트")
        st.markdown(st.session_state['consumer_analysis'])
        st.divider()
        st.subheader("🔍 수집된 원본 데이터 (Raw Data)")
        st.table(pd.DataFrame(st.session_state['consumer_data'])) # 원본 복구

# [STEP 3] 최종 전략 도출 (Gap 분석 고도화)
elif menu == "STEP 3. 전략적 Gap 도출":
    st.title("🧠 STEP 3. 입체적 Gap 분석 및 광고 전략")
    if not st.session_state['brand_analysis'] or not st.session_state['consumer_analysis']:
        st.warning("이전 단계 분석을 완료해주세요.")
    else:
        if st.button("🚀 최종 전략 리포트 생성"):
            validate_keys()
            with st.spinner("전략적 핵심 간극을 도출 중..."):
                client = genai.Client(api_key=gemini_key)
                prompt = f"""
                당신은 광고 대행사 총괄 기획자입니다. 자사/경쟁사/소비자 데이터를 대조하여 필승 전략을 도출하세요.
                
                [자사 분석]: {st.session_state['brand_analysis']}
                [경쟁사 분석]: {st.session_state['comp_analysis']}
                [소비자 분석]: {st.session_state['consumer_analysis']}
                
                작성 가이드:
                1. 브랜드 언어 vs 소비자 언어 Gap 분석: 브랜드가 사용하는 '전문 용어'와 소비자가 사용하는 '일상 용어'를 표 형태로 대조.
                2. 경쟁사 대비 White Space: 경쟁사는 말하고 있지 않지만 소비자가 간절히 원하는 '기회 영역' 도출.
                3. 소비자 언어 기반 DA 전략: 실제 수집된 소비자 키워드를 활용한 3가지 DA 카피 소재와 비주얼 방향성.
                4. 결론: 소비자의 어떤 '결핍'을 자사의 어떤 'USP'로 해결할 것인지 1줄 정의.
                """
                st.session_state['final_report'] = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt).text
                st.rerun()

        if st.session_state['final_report']:
            st.markdown(st.session_state['final_report'])
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            with c1: i1 = st.checkbox("브랜드 분석", value=True)
            with c2: i2 = st.checkbox("경쟁사 분석", value=True)
            with c3: i3 = st.checkbox("소비자 분석", value=True)
            with c4: i4 = st.checkbox("최종 전략", value=True)
            
            exp = []
            if i1: exp.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
            if i2: exp.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
            if i3: exp.append(("CONSUMER ANALYSIS", st.session_state['consumer_analysis']))
            if i4: exp.append(("FINAL STRATEGY", st.session_state['final_report']))
            
            if exp:
                pdf = generate_pdf(exp)
                st.download_button("📥 통합 리포트 PDF 다운로드", data=pdf, file_name="Total_Strategy.pdf")
