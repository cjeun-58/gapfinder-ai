import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io
import os
import re

# --- 1. 페이지 설정 및 데이터 초기화 ---
_ = st.set_page_config(page_title="GapFinder AI v18.0", layout="wide")

states = ['brand_analysis', 'brand_insight', 'comp_analysis', 'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = [] if 'data' in key else ""

# --- 2. 사이드바 (실시간 분석 현황 복구) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    _ = st.divider()
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 자사 분석 & 인사이트", 
        "STEP 1.5. 경쟁사 Deep-Dive", 
        "STEP 2. 소비자 데이터 탐색", 
        "STEP 3. 전략 리포트 및 PDF"
    ])
    _ = st.divider()
    
    # [복구] 실시간 분석 현황표
    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 자사 분석: {'✅ 완료' if st.session_state['brand_analysis'] else '❌ 미완료'}")
    st.write(f"⚔️ 경쟁사 분석: {'✅ 완료' if st.session_state['comp_analysis'] else '❌ 미완료'}")
    st.write(f"👥 소비자 분석: {'✅ 완료' if st.session_state['consumer_analysis'] else '❌ 미완료'}")

# --- 3. 핵심 유틸리티 함수 ---

def extract_text(files=None, urls=None):
    text = ""
    if files:
        for f in files:
            try:
                if f.name.endswith(".pdf"): text += "\n".join([p.extract_text() for p in PdfReader(f).pages if p.extract_text()])
                elif f.name.endswith(".pptx"): text += "\n".join([s.text for slide in Presentation(f).slides for s in slide.shapes if hasattr(s, "text")])
                elif f.name.endswith(".xlsx"): text += pd.read_excel(f).to_string()
            except: pass
    if urls:
        for url in urls:
            if url and url.strip():
                try:
                    res = requests.get(url.strip(), headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    for s in soup(['script', 'style']): s.decompose()
                    text += f"\n[참조: {url}]\n{soup.get_text()[:3000]}"
                except: pass
    return text

def analyze_strategy(content, target_type, insight="", brand_context="", consumer_raw=""):
    """v6.5의 필승 전략 공식과 v14의 Gap 분석을 결합한 엔진"""
    try:
        client = genai.Client(api_key=gemini_key)
        p_base = "인사말 생략. 광고 대행사 총괄 기획자로서 분석하세요. 리스트 형식을 사용하세요.\n\n"
        
        prompts = {
            "brand": f"{p_base}[Brand Analysis] 자사의 핵심 USP와 운영 인사이트를 분석하세요. 인사이트: {insight}",
            "comp": f"{p_base}[Competitor Analysis] 경쟁사들의 소구점을 매트릭스로 분석하세요. 자사({brand_context[:200]})와의 차별점(White Space)을 발굴하세요.",
            "consumer": f"{p_base}[Consumer Real Voice] 소비자들의 날것의 페인포인트를 분석하세요. [데이터 #번] 태그를 반드시 붙이세요.",
            "final": f"{p_base}[Strategic Gap Report]\n1. 브랜드 언어 vs 소비자 언어 Gap 분석: 브랜드가 말하는 가치(Value)와 소비자가 원하는 실익(Utility)을 워딩 대조를 통해 분석하세요.\n2. 경쟁사 대비 White Space 도출\n3. 타겟별 DA 광고 카피 및 비주얼 제안\n4. 최종 결론: v6.5 스타일의 'Victory Strategy' 필승 전략 한 문장 정의\n자사 인사이트: {insight}\n소비자 데이터: {consumer_raw[:6000]}"
        }
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[target_type] + "\n\n데이터:\n" + content[:12000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 무결점 PDF 엔진 (Iron Guard v2) ---

class IronPDF(FPDF):
    def __init__(self):
        super().__init__()
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg):
            self.add_font('NG', '', f_reg); self.add_font('NG', 'B', f_bold); self.fn = 'NG'
        else: self.fn = 'Arial'
        _ = self.set_auto_page_break(auto=True, margin=20)
        _ = self.set_margins(20, 20, 20)

    def header(self):
        if self.page_no() == 1:
            _ = self.set_font(self.fn, 'B', 18); _ = self.set_text_color(0, 51, 102)
            _ = self.cell(170, 15, txt="Strategic Gap Analysis Report", ln=True, align='C'); _ = self.ln(5)

    def write_safe(self, text):
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: _ = self.ln(5); continue
            _ = self.set_font(self.fn, '', 10); _ = self.set_text_color(50, 50, 50)
            if line.startswith('##') or line.startswith('1.') or 'Strategy' in line or line.startswith('#'): 
                _ = self.set_font(self.fn, 'B', 12)
            # 인코딩 에러 및 잘림 방지를 위해 특수문자 제거 후 170mm 폭 고정 출력
            clean = re.sub(r'[^\u0000-\u007f\uac00-\ud7af]', '', line.replace('|', ' '))
            _ = self.multi_cell(170, 7, txt=clean)

# --- 5. 화면 레이아웃 및 실행 ---

if menu == "STEP 1. 자사 분석 & 인사이트":
    st.title("🏢 STEP 1. 자사 정체성 및 인사이트 분석")
    b_f = st.file_uploader("자사 자료 업로드 (PDF, PPTX 등)", accept_multiple_files=True)
    b_u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 실제 운영 인사이트 (과거 데이터 피드백)", value=st.session_state['brand_insight'], height=150)
    if st.button("자사 분석 실행"):
        with st.spinner("자산 분석 중..."):
            st.session_state['brand_analysis'] = analyze_strategy(extract_text(b_f, [b_u]), "brand", st.session_state['brand_insight'])
            _ = st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 Deep-Dive":
    st.title("⚔️ STEP 1.5. 경쟁사 다중 비교 분석")
    c_f = st.file_uploader("경쟁사 자료 업로드", accept_multiple_files=True)
    col1, col2 = st.columns([1, 2])
    with col1: c1n = st.text_input("경쟁사 1"); c2n = st.text_input("경쟁사 2")
    with col2: c1u = st.text_input("경쟁사 1 URL"); c2u = st.text_input("경쟁사 2 URL")
    if st.button("경쟁사 정밀 탐색"):
        with st.spinner("경쟁사 소구점 매핑 중..."):
            all_c = extract_text(c_f, [c1u, c2u])
            for n in [c1n, c2n]:
                if n:
                    res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{n} 마케팅 특징", "gl": "kr", "hl": "ko"}).json()
                    all_c += f"\n[{n}]\n" + "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
            st.session_state['comp_analysis'] = analyze_strategy(all_c, "comp", brand_context=st.session_state['brand_analysis'])
            _ = st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 데이터 탐색":
    st.title("👥 STEP 2. 소비자 리얼 보이스 데이터")
    kw = st.text_input("분석 키워드")
    if st.button("데이터 수집 시작"):
        with st.spinner("수집 중..."):
            all_r = []
            for qs in ["후기", "단점", "실망"]:
                res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{kw} {qs}", "num": 15, "gl": "kr", "hl": "ko"}).json()
                if 'organic' in res: all_r.extend([{'title': r.get('title'), 'body': r.get('snippet')} for r in res['organic']])
            st.session_state['consumer_data'] = all_r
            st.session_state['consumer_analysis'] = analyze_strategy(str(all_r), "consumer")
            _ = st.rerun()
    if st.session_state['consumer_analysis']: 
        st.markdown(st.session_state['consumer_analysis'])
        _ = st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 전략 리포트 및 PDF":
    st.title("🧠 STEP 3. 전략적 Gap 도출 및 리포트")
    if st.button("🚀 최종 리포트 생성"):
        with st.spinner("데이터 합성 중..."):
            comb = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_strategy(comb, "final", st.session_state['brand_insight'], consumer_raw=str(st.session_state['consumer_data']))
            _ = st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        _ = st.divider()
        st.subheader("📥 선택 섹션 통합 다운로드 (Iron Guard v2)")
        c1, c2, c3, c4 = st.columns(4)
        with c1: i1 = st.checkbox("자사", value=True)
        with c2: i2 = st.checkbox("경쟁사", value=True)
        with c3: i3 = st.checkbox("소비자", value=True)
        with c4: i4 = st.checkbox("전략", value=True)
        exp = []
        if i1: _ = exp.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
        if i2: _ = exp.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
        if i3: _ = exp.append(("CONSUMER EVIDENCE", st.session_state['consumer_analysis']))
        if i4: _ = exp.append(("FINAL STRATEGY master", st.session_state['final_report']))
        
        if exp:
            pdf = IronPDF(); _ = pdf.add_page()
            for t, b in exp:
                _ = pdf.set_fill_color(240, 240, 240); _ = pdf.set_font(pdf.fn, 'B', 12)
                _ = pdf.cell(170, 10, txt=f" {t}", ln=True, fill=True); _ = pdf.ln(3)
                _ = pdf.write_safe(b); _ = pdf.ln(8)
            _ = st.download_button("📥 통합 리포트 PDF 다운로드 (One-Click)", data=bytes(pdf.output()), file_name="Total_Strategy_Report.pdf", mime="application/pdf")
