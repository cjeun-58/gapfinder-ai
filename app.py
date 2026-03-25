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
_ = st.set_page_config(page_title="GapFinder AI v14.4", layout="wide")

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
    menu = st.radio("전략 수립 단계", ["STEP 1. 자사 분석", "STEP 1.5. 경쟁사 분석", "STEP 2. 소비자 분석", "STEP 3. 하이브리드 전략 & PDF"])
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
                    text += f"\n[참조내용: {url}]\n{soup.get_text()[:3000]}"
                except Exception: pass
    return text

def analyze_hybrid(content, target_type, insight="", brand_context=""):
    try:
        client = genai.Client(api_key=gemini_key)
        p_base = "인사말 생략. 광고 대행사 총괄 기획자로서 분석하세요. 리스트 형식을 사용하되 Gap 분석은 구체적인 대조를 포함하세요.\n\n"
        
        # [핵심] Gap 분석을 강제하는 프롬프트 튜닝
        prompts = {
            "brand": f"{p_base}[Thesis] 자사 브랜드 가치와 운영 인사이트를 대조하여 페르소나를 정의하세요. 인사이트: {insight}",
            "comp": f"{p_base}[Competitor] 경쟁사 소구점을 분석하세요. 자사({brand_context[:300]})와 겹치는 레드오션과 비어있는 화이트스페이스를 찾아내세요.",
            "consumer": f"{p_base}[Antithesis] 소비자들의 '날것의 불편(Raw Voice)'을 수집 데이터 기반으로 도출하세요.",
            "final": f"{p_base}[Hybrid Strategy]\n1. 브랜드 vs 소비자 언어 Gap 분석: 브랜드가 말하는 가치와 소비자가 생각하는 실익의 간극을 구체적 워딩으로 대조하세요.\n2. 경쟁사 대비 White Space: 경쟁사의 한계와 소비자의 숨겨진 니즈가 만나는 기회 영역을 도출하세요.\n3. 정반합 결론 및 DA 카피: 간극을 메우는 필승 전략과 타겟별 광고 카피를 제안하세요.\n인사이트: {insight}"
        }
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[target_type] + "\n\n데이터:\n" + content[:12000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 무결점 PDF 엔진 (에러 완벽 차단) ---

class MasterPDF(FPDF):
    def __init__(self):
        super().__init__()
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg) and os.path.exists(f_bold):
            self.add_font('NG', '', f_reg); self.add_font('NG', 'B', f_bold); self.font_family_k = 'NG'
        else: self.font_family_k = 'Arial'
        _ = self.set_auto_page_break(auto=True, margin=15)
        # 마진을 명시적으로 고정하여 너비 계산 에러 방지
        self.l_m, self.r_m = 20, 20
        _ = self.set_margins(self.l_m, 15, self.r_m)

    def header(self):
        if hasattr(self, 'font_family_k') and self.page_no() == 1:
            _ = self.set_font(self.font_family_k, 'B', 20); _ = self.set_text_color(0, 51, 102)
            _ = self.cell(0, 20, txt="Hybrid Strategy Gap Analysis Report", ln=True, align='C'); _ = self.ln(5)

    def write_smart(self, text):
        # [해결] 가용 너비를 강제 계산하여 'Not enough horizontal space' 에러 차단
        eff_w = self.w - self.l_m - self.r_m
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: _ = self.ln(5); continue
            _ = self.set_font(self.font_family_k, '', 10.5); _ = self.set_text_color(50, 50, 50)
            if line.startswith('##') or line.startswith('1.') or line.startswith('2.') or '전략' in line: 
                _ = self.set_font(self.font_family_k, 'B', 13)
            clean = re.sub(r'[^\u0000-\u007f\uac00-\ud7af]', '', line.replace('|', ' '))
            _ = self.multi_cell(eff_w, 7, txt=clean) # 너비를 eff_w로 고정

# --- 5. 화면 레이아웃 및 실행 로직 ---

if menu == "STEP 1. 자사 분석":
    st.title("🏢 STEP 1. 자사 분석 및 인사이트")
    b_f = st.file_uploader("자사 자료 (PDF, PPTX 등)", accept_multiple_files=True)
    b_u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 운영 인사이트 (실제 효율 데이터 등)", value=st.session_state['brand_insight'], height=150)
    if st.button("자사 분석 실행"):
        with st.spinner("자산 분석 중..."):
            st.session_state['brand_analysis'] = analyze_hybrid(extract_text(b_f, [b_u]), "brand", st.session_state['brand_insight'])
            _ = st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 분석":
    st.title("⚔️ STEP 1.5. 경쟁사 다중 비교 분석")
    c_f = st.file_uploader("경쟁사 전용 자료 업로드", accept_multiple_files=True)
    col1, col2 = st.columns([1, 2])
    with col1: c1_n = st.text_input("경쟁사 1"); c2_n = st.text_input("경쟁사 2"); c3_n = st.text_input("경쟁사 3")
    with col2: c1_u = st.text_input("경쟁사 1 URL"); c2_u = st.text_input("경쟁사 2 URL"); c3_u = st.text_input("경쟁사 3 URL")
    if st.button("경쟁사 정밀 분석"):
        with st.spinner("경쟁사 탐색 중..."):
            all_c = extract_text(c_f, [c1_u, c2_u, c3_u])
            for n in [c1_n, c2_n, c3_n]:
                if n:
                    res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{n} 특징 마케팅 전략", "gl": "kr", "hl": "ko"}).json()
                    if 'organic' in res: all_c += f"\n[{n}]\n" + "\n".join([r.get('snippet', '') for r in res['organic']])
            st.session_state['comp_analysis'] = analyze_hybrid(all_c, "comp", brand_context=st.session_state['brand_analysis'])
            _ = st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 분석":
    st.title("👥 STEP 2. 소비자 리얼 보이스 데이터")
    kw = st.text_input("분석 키워드"); ex = st.text_input("제외 키워드")
    if st.button("데이터 수집"):
        with st.spinner("대량 수집 및 필터링 중..."):
            all_r = []
            for qs in ["후기", "단점", "실망"]:
                res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{kw} {qs} {f'-{ex}' if ex else ''}", "num": 20, "gl": "kr", "hl": "ko"}).json()
                if 'organic' in res: all_r.extend([{'title': r.get('title'), 'body': r.get('snippet'), 'link': r.get('link')} for r in res['organic']])
            st.session_state['consumer_data'] = all_r
            st.session_state['consumer_analysis'] = analyze_hybrid(str(all_r), "consumer")
            _ = st.rerun()
    if st.session_state['consumer_analysis']: 
        st.markdown(st.session_state['consumer_analysis'])
        _ = st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 하이브리드 전략 & PDF":
    st.title("🧠 STEP 3. GAP FINDER & 정반합 통합 전략")
    if st.button("🚀 최종 통합 리포트 생성"):
        with st.spinner("데이터 합성 중..."):
            comb = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_hybrid(comb, "final", st.session_state['brand_insight'])
            _ = st.rerun()
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        _ = st.divider()
        st.subheader("📥 선택 섹션 통합 다운로드")
        c1, c2, c3, c4 = st.columns(4)
        with c1: i1 = st.checkbox("자사", value=True)
        with c2: i2 = st.checkbox("경쟁사", value=True)
        with c3: i3 = st.checkbox("소비자", value=True)
        with c4: i4 = st.checkbox("최종전략", value=True)
        exp = []
        if i1: _ = exp.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
        if i2: _ = exp.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
        if i3: _ = exp.append(("CONSUMER ANALYSIS", st.session_state['consumer_analysis']))
        if i4: _ = exp.append(("GAP STRATEGY REPORT", st.session_state['final_report']))
        if exp:
            pdf = MasterPDF(); _ = pdf.add_page()
            for t, b in exp:
                _ = pdf.set_fill_color(240, 240, 240); _ = pdf.set_font(pdf.font_family_k, 'B', 14)
                _ = pdf.cell(0, 12, txt=f" {t}", ln=True, fill=True); _ = pdf.ln(3)
                _ = pdf.write_smart(b); _ = pdf.ln(8)
            _ = st.download_button("📥 통합 리포트 PDF 다운로드 (One-Click)", data=bytes(pdf.output()), file_name="Strategy_Report.pdf", mime="application/pdf")
