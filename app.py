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
_ = st.set_page_config(page_title="GapFinder AI v14.0", layout="wide")

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
        "STEP 2. 소비자 분석 (Antithesis)", 
        "STEP 3. 하이브리드 전략 및 PDF"
    ])
    _ = st.divider()
    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 자사: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 유틸리티 함수 ---
def extract_text(files, urls=None):
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
            if url:
                try:
                    res = requests.get(url.strip(), headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    text += f"\n[URL내용: {url}]\n{BeautifulSoup(res.text, 'html.parser').get_text()[:3000]}"
                except: pass
    return text

def analyze_hybrid(content, target_type, insight=""):
    try:
        client = genai.Client(api_key=gemini_key)
        p_base = "자기소개 금지. 광고 대행사의 시각으로 분석하세요. 리스트 형식을 사용하세요.\n\n"
        
        prompts = {
            "brand": f"{p_base}[Thesis] 자사 브랜드 가치와 아래 운영 인사이트를 대조하여 분석하세요. 인사이트: {insight}",
            "comp": f"{p_base}[Competitor Analysis] 여러 경쟁사의 소구점을 각각 분석하고 비교 매트릭스를 구성하세요.",
            "consumer": f"{p_base}[Antithesis] 소비자의 날것의 언어와 결핍(Needs)을 분석하세요.",
            "final": f"{p_base}[Hybrid Strategy]\n1. GAP FINDER: 자사 vs 경쟁사 vs 소비자의 언어 대조표를 작성하고 우리가 잘하는 점/못하는 점을 비판적으로 분석하세요.\n2. Synthesis: 위 대조를 바탕으로 '정반합' 결론을 도출하고 실제 DA 카피 소재를 제안하세요.\n인사이트: {insight}"
        }
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[target_type] + "\n\n데이터:\n" + content[:12000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. PDF 엔진 (None 방어) ---
class MasterPDF(FPDF):
    def __init__(self):
        super().__init__()
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg) and os.path.exists(f_bold):
            self.add_font('NG', '', f_reg); self.add_font('NG', 'B', f_bold); self.font_family_k = 'NG'
        else: self.font_family_k = 'Arial'
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(20, 15, 20)

    def header(self):
        if hasattr(self, 'font_family_k') and self.page_no() == 1:
            self.set_font(self.font_family_k, 'B', 20); self.set_text_color(0, 51, 102)
            self.cell(0, 20, txt="Hybrid Strategy Gap Analysis Report", ln=True, align='C'); self.ln(5)

    def write_smart(self, text):
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: self.ln(5); continue
            self.set_font(self.font_family_k, '', 10.5); self.set_text_color(50, 50, 50)
            if line.startswith('##') or line.startswith('1.') or line.startswith('2.'): 
                self.set_font(self.font_family_k, 'B', 14); line = line.replace('##', '')
            clean = re.sub(r'[^\u0000-\u007f\uac00-\ud7af]', '', line.replace('|', ' '))
            self.multi_cell(0, 7, txt=clean)

# --- 5. 단계별 실행 ---

if menu == "STEP 1. 자사 분석 (Thesis)":
    st.title("🏢 STEP 1. 자사 정체성 분석") [cite: 176]
    b_files = st.file_uploader("자사 자료 (PDF, PPTX 등)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    b_url = st.text_input("자사 사이트 URL")
    st.session_state['brand_insight'] = st.text_area("💡 실제 운영 인사이트 (해봤는데 안 통했던 것 등)", value=st.session_state['brand_insight']) [cite: 403]
    if st.button("분석 실행"):
        with st.spinner("자산 분석 중..."):
            st.session_state['brand_analysis'] = analyze_hybrid(extract_text(b_files, [b_url]), "brand", st.session_state['brand_insight'])
            _ = st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 Deep-Dive":
    st.title("⚔️ STEP 1.5. 경쟁사 분석 (최대 3개 세트)") [cite: 177]
    st.markdown("경쟁사 명칭과 URL을 세트로 입력하세요. 자료가 있다면 파일도 추가 가능합니다.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        c1_n = st.text_input("경쟁사 1 이름")
        c2_n = st.text_input("경쟁사 2 이름")
        c3_n = st.text_input("경쟁사 3 이름")
    with col2:
        c1_u = st.text_input("경쟁사 1 URL")
        c2_u = st.text_input("경쟁사 2 URL")
        c3_u = st.text_input("경쟁사 3 URL")
        
    c_files = st.file_uploader("경쟁사 추가 자료 업로드", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    
    if st.button("경쟁사 정밀 분석 실행"):
        with st.spinner("경쟁사별 소구점 탐색 중..."):
            all_c = extract_text(c_files, [c1_u, c2_u, c3_u])
            for name in [c1_n, c2_n, c3_n]:
                if name:
                    res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{name} 제품 특징 마케팅", "gl": "kr", "hl": "ko"}).json()
                    all_c += f"\n[{name}]\n" + "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
            st.session_state['comp_analysis'] = analyze_hybrid(all_c, "comp")
            _ = st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 분석 (Antithesis)":
    st.title("👥 STEP 2. 소비자 언어 탐색") [cite: 178]
    kw = st.text_input("분석 키워드")
    ex = st.text_input("제외 키워드", value="항공, 일본")
    if st.button("데이터 수집"):
        with st.spinner("수집 중..."):
            all_d = []
            for q in [f"{kw} 후기", f"{kw} 단점", f"{kw} 실망"]:
                res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{q} -{ex}", "num": 20, "gl": "kr", "hl": "ko"}).json()
                all_d.extend([{'title': r.get('title'), 'body': r.get('snippet')} for r in res.get('organic', [])])
            st.session_state['consumer_data'] = all_d
            st.session_state['consumer_analysis'] = analyze_hybrid(str(all_d), "consumer")
            _ = st.rerun()
    if st.session_state['consumer_analysis']: 
        st.markdown(st.session_state['consumer_analysis'])
        _ = st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 하이브리드 전략 및 PDF":
    st.title("🧠 STEP 3. GAP FINDER & 정반합 전략") [cite: 181-182]
    if st.button("🚀 하이브리드 리포트 생성"):
        with st.spinner("데이터 대조 및 합성 중..."):
            d = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_hybrid(d, "final", st.session_state['brand_insight'])
            _ = st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        _ = st.divider()
        st.subheader("📥 선택 섹션 통합 다운로드")
        c1, c2, c3, c4 = st.columns(4)
        with c1: i1 = st.checkbox("자사", value=True); with c2: i2 = st.checkbox("경쟁사", value=True)
        with c3: i3 = st.checkbox("소비자", value=True); with c4: i4 = st.checkbox("최종전략", value=True)
        
        exp = []
        if i1: _ = exp.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
        if i2: _ = exp.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
        if i3: _ = exp.append(("CONSUMER ANALYSIS", st.session_state['consumer_analysis']))
        if i4: _ = exp.append(("HYBRID STRATEGY REPORT", st.session_state['final_report']))
        
        if exp:
            pdf = MasterPDF(); _ = pdf.add_page()
            for t, b in exp:
                _ = pdf.set_fill_color(240, 240, 240); _ = pdf.set_font(pdf.font_family_k, 'B', 14)
                _ = pdf.cell(0, 12, txt=f" {t}", ln=True, fill=True); _ = pdf.ln(3)
                _ = pdf.write_smart(b); _ = pdf.ln(8)
            _ = st.download_button("📥 통합 리포트 다운로드 (One-Click)", data=bytes(pdf.output()), file_name="Hybrid_Strategy_Report.pdf", mime="application/pdf")
