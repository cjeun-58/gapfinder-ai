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
_ = st.set_page_config(page_title="GapFinder AI v15.0", layout="wide")

# 세션 데이터 초기화 (분석 일관성 유지)
states = ['brand_analysis', 'brand_insight', 'comp_analysis', 'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = [] if 'data' in key else ""

# --- 2. 사이드바 (실시간 현황) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    _ = st.divider()
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 자사 분석 (Thesis)", 
        "STEP 1.5. 경쟁사 Deep-Dive", 
        "STEP 2. 소비자 데이터 (Evidence)", 
        "STEP 3. 전략 리포트 (Victory Strategy)"
    ])
    _ = st.divider()
    st.subheader("📊 분석 현황")
    st.write(f"🏢 자사: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 유틸리티 함수 ---

def extract_text(files=None, urls=None):
    text = ""
    if files:
        for f in files:
            try:
                if f.name.endswith(".pdf"): text += "\n".join([p.extract_text() for p in PdfReader(f).pages if p.extract_text()])
                elif f.name.endswith(".pptx"): text += "\n".join([s.text for slide in Presentation(f).slides for s in slide.shapes if hasattr(s, "text")])
                elif f.name.endswith(".xlsx"): text += pd.read_excel(f).to_string()
            except Exception: pass
    if urls:
        for url in urls:
            if url and url.strip():
                try:
                    res = requests.get(url.strip(), headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    for s in soup(['script', 'style']): s.decompose()
                    text += f"\n[참조: {url}]\n{soup.get_text()[:3000]}"
                except Exception: pass
    return text

def analyze_with_evidence(content, target_type, insight="", brand_context="", consumer_raw=""):
    """
    [v15.0 핵심] 모든 분석에 데이터 근거(Evidence Tag)를 강제하는 로직
    """
    try:
        client = genai.Client(api_key=gemini_key)
        p_base = "자기소개 생략. 광고 대행사 총괄 기획자로서 분석하세요. 모든 전략적 제언 뒤에는 반드시 [근거: 소비자 언어 '...'] 또는 [근거: 데이터 #번]과 같은 태그를 붙이세요.\n\n"
        
        prompts = {
            "brand": f"{p_base}[Thesis] 자사 브랜드 가치 분석. 인사이트: {insight}",
            "comp": f"{p_base}[Competitor] 경쟁사 분석. 자사({brand_context[:200]})와 대조하여 화이트스페이스 도출.",
            "consumer": f"{p_base}[Evidence] 소비자 Raw Voice 수집 및 페인포인트 분류. 각 항목에 데이터 인덱스 번호를 부여하세요.",
            "final": f"{p_base}[Victory Strategy]\n1. 브랜드 vs 소비자 언어 Gap 분석 (근거 태그 필수)\n2. 경쟁사 대비 White Space 도출\n3. 타겟별 DA 카피 및 비주얼 제안 (각 카피마다 근거가 된 소비자 워딩 명시)\n4. 결론: v6.5 스타일의 'Victory Strategy' 한 문장 정의\n자사 인사이트: {insight}\n소비자 데이터: {consumer_raw[:5000]}"
        }
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[target_type] + "\n\n데이터:\n" + content[:12000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 무결점 PDF 엔진 ---

class MasterPDF(FPDF):
    def __init__(self):
        super().__init__()
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg) and os.path.exists(f_bold):
            self.add_font('NG', '', f_reg); self.add_font('NG', 'B', f_bold); self.font_family_k = 'NG'
        else: self.font_family_k = 'Arial'
        _ = self.set_auto_page_break(auto=True, margin=15)
        self.l_m, self.r_m = 20, 20
        _ = self.set_margins(self.l_m, 15, self.r_m)

    def header(self):
        if hasattr(self, 'font_family_k') and self.page_no() == 1:
            _ = self.set_font(self.font_family_k, 'B', 20); _ = self.set_text_color(0, 51, 102)
            _ = self.cell(0, 20, txt="Strategic Evidence Master Report", ln=True, align='C'); _ = self.ln(5)

    def write_smart(self, text):
        eff_w = self.w - self.l_m - self.r_m
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: _ = self.ln(5); continue
            _ = self.set_font(self.font_family_k, '', 10.5); _ = self.set_text_color(50, 50, 50)
            if line.startswith('##') or line.startswith('1.') or 'Strategy' in line: 
                _ = self.set_font(self.font_family_k, 'B', 13)
            clean = re.sub(r'[^\u0000-\u007f\uac00-\ud7af]', '', line.replace('|', ' '))
            _ = self.multi_cell(eff_w, 7, txt=clean)

# --- 5. 화면 레이아웃 및 실행 ---

if menu == "STEP 1. 자사 분석 (Thesis)":
    st.title("🏢 STEP 1. 자사 정체성 분석")
    b_f = st.file_uploader("자사 자료 업로드", accept_multiple_files=True)
    b_u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 운영 인사이트 (현장 피드백)", value=st.session_state['brand_insight'], height=150)
    if st.button("분석 실행"):
        with st.spinner("분석 중..."):
            st.session_state['brand_analysis'] = analyze_with_evidence(extract_text(b_f, [b_u]), "brand", st.session_state['brand_insight'])
            _ = st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 Deep-Dive":
    st.title("⚔️ STEP 1.5. 경쟁사 다중 분석")
    c_f = st.file_uploader("경쟁사 전용 자료", accept_multiple_files=True)
    col1, col2 = st.columns([1, 2])
    with col1: c1_n = st.text_input("경쟁사 1"); c2_n = st.text_input("경쟁사 2"); c3_n = st.text_input("경쟁사 3")
    with col2: c1_u = st.text_input("경쟁사 1 URL"); c2_u = st.text_input("경쟁사 2 URL"); c3_u = st.text_input("경쟁사 3 URL")
    if st.button("경쟁사 분석"):
        with st.spinner("탐색 중..."):
            all_c = extract_text(c_f, [c1_u, c2_u, c3_u])
            for n in [c1_n, c2_n, c3_n]:
                if n:
                    res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{n} 특징 마케팅", "gl": "kr", "hl": "ko"}).json()
                    all_c += f"\n[{n}]\n" + "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
            st.session_state['comp_analysis'] = analyze_with_evidence(all_c, "comp", brand_context=st.session_state['brand_analysis'])
            _ = st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 데이터 (Evidence)":
    st.title("👥 STEP 2. 소비자 데이터 수집 및 태깅")
    kw = st.text_input("분석 키워드")
    if st.button("데이터 수집"):
        with st.spinner("멀티 채널 수집 중..."):
            all_r = []
            for qs in ["후기", "단점", "실망"]:
                res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{kw} {qs}", "num": 20, "gl": "kr", "hl": "ko"}).json()
                if 'organic' in res: all_r.extend([{'title': r.get('title'), 'body': r.get('snippet')} for r in res['organic']])
            st.session_state['consumer_data'] = all_r
            st.session_state['consumer_analysis'] = analyze_with_evidence(str(all_r), "consumer")
            _ = st.rerun()
    if st.session_state['consumer_analysis']: 
        st.markdown(st.session_state['consumer_analysis'])
        _ = st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 전략 리포트 (Victory Strategy)":
    st.title("🧠 STEP 3. 에비던스 기반 Victory Strategy")
    if st.button("🚀 통합 전략 리포트 도출"):
        with st.spinner("데이터 매핑 및 합성 중..."):
            comb = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_with_evidence(comb, "final", st.session_state['brand_insight'], consumer_raw=str(st.session_state['consumer_data']))
            _ = st.rerun()
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        _ = st.divider()
        c1, c2, c3, c4 = st.columns(4)
        with c1: i1 = st.checkbox("자사", value=True)
        with c2: i2 = st.checkbox("경쟁사", value=True)
        with c3: i3 = st.checkbox("소비자", value=True)
        with c4: i4 = st.checkbox("전략", value=True)
        exp = []
        if i1: _ = exp.append(("BRAND", st.session_state['brand_analysis']))
        if i2: _ = exp.append(("COMPETITOR", st.session_state['comp_analysis']))
        if i3: _ = exp.append(("CONSUMER DATA", st.session_state['consumer_analysis']))
        if i4: _ = exp.append(("VICTORY STRATEGY", st.session_state['final_report']))
        if exp:
            pdf = MasterPDF(); _ = pdf.add_page()
            for t, b in exp:
                _ = pdf.set_fill_color(240, 240, 240); _ = pdf.set_font(pdf.font_family_k, 'B', 14)
                _ = pdf.cell(0, 12, txt=f" {t}", ln=True, fill=True); _ = pdf.ln(3)
                _ = pdf.write_smart(b); _ = pdf.ln(8)
            _ = st.download_button("📥 통합 리포트 다운로드 (One-Click)", data=bytes(pdf.output()), file_name="Evidence_Strategy_Report.pdf", mime="application/pdf")
