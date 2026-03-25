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
_ = st.set_page_config(page_title="GapFinder AI v19.0", layout="wide")

# 세션 상태 초기화 (사이드바 ✅ 표시 및 데이터 유지)
states = ['brand_analysis', 'brand_insight', 'comp_analysis', 'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key else []
if 'brand_insight' not in st.session_state:
    st.session_state['brand_insight'] = ""

# --- 2. 사이드바 (실시간 분석 현황 ✅) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    _ = st.divider()
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 자사 분석 (Thesis)", 
        "STEP 1.5. 경쟁사 분석 (3 Sets)", 
        "STEP 2. 소비자 데이터 (Multi-KW)", 
        "STEP 3. 최종 전략 및 PDF"
    ])
    _ = st.divider()
    st.subheader("📊 실시간 분석 현황")
    # [복구] 사이드바 상태 체크 표시
    st.write(f"🏢 자사 분석: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사 분석: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자 분석: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

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
                    text += f"\n[참조내용: {url}]\n{soup.get_text()[:2500]}"
                except: pass
    return text

def analyze_ai(content, target_type, insight="", brand_context="", consumer_raw=""):
    """v6.5의 직관적 결론과 데이터 근거를 결합한 분석 엔진"""
    try:
        client = genai.Client(api_key=gemini_key)
        p_base = "자기소개 생략. 광고 기획자로서 리스트 형식으로 분석하세요. 모든 제언 뒤에 [근거: 소비자 언어 '...'] 태그를 붙이세요.\n\n"
        
        prompts = {
            "brand": f"{p_base}[Thesis] 자사 브랜드 정체성 및 인사이트 분석. 인사이트: {insight}",
            "comp": f"{p_base}[Competitor] 오직 입력된 경쟁사만 분석하세요. 임의로 다른 브랜드를 추가하지 마세요. 자사({brand_context[:200]})와의 1:1 차별점에 집중하세요.",
            "consumer": f"{p_base}[Evidence] 소비자 Raw Voice 분석. 페인포인트별로 번호를 부여하세요.",
            "final": f"{p_base}[Victory Strategy]\n1. 브랜드 언어 vs 소비자 언어 Gap 분석: 브랜드의 가치(Value)와 소비자의 실속(Utility)을 1:1 워딩 대조를 통해 분석하세요.\n2. 경쟁사 대비 White Space 도출\n3. 타겟별 DA 카피 (소비자 워딩 인용)\n4. 최종 결론: v6.5 스타일 필승 전략 정의\n자사 인사이트: {insight}\n소비자 데이터: {consumer_raw[:5000]}"
        }
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[target_type] + "\n\n데이터:\n" + content[:12000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 무결점 PDF 엔진 (잘림 방지 최우선) ---

class SafePDF(FPDF):
    def __init__(self):
        super().__init__()
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg):
            self.add_font('NG', '', f_reg); self.add_font('NG', 'B', f_bold); self.fn = 'NG'
        else: self.fn = 'Arial'
        
        _ = self.set_auto_page_break(auto=True, margin=20)
        self.l_m, self.r_m = 25, 25 
        _ = self.set_margins(self.l_m, 20, self.r_m)

    def header(self):
        if self.page_no() == 1:
            self.set_font(self.fn, 'B', 16); self.set_text_color(0, 51, 102)
            self.cell(160, 15, txt="Strategic Gap Analysis Report", ln=True, align='C'); self.ln(5)

    def write_text(self, text):
        eff_w = 160 # 고정 너비로 잘림 원천 차단
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: self.ln(5); continue
            self.set_font(self.fn, '', 10); self.set_text_color(50, 50, 50)
            if line.startswith('#') or line.startswith('1.') or 'Strategy' in line: 
                self.set_font(self.fn, 'B', 12)
            # 특수 기호 정제 및 안전 출력
            clean = re.sub(r'[^\u0000-\u007f\uac00-\ud7af]', '', line.replace('|', ' '))
            self.multi_cell(eff_w, 7, txt=clean)

# --- 5. 단계별 실행 로직 ---

if menu == "STEP 1. 자사 분석 (Thesis)":
    st.title("🏢 STEP 1. 자사 정체성 분석")
    b_f = st.file_uploader("자사 자료 업로드 (PDF, PPTX 등)", accept_multiple_files=True)
    b_u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 운영 인사이트 (과거 데이터 피드백 등)", value=st.session_state['brand_insight'], height=100)
    if st.button("자사 분석 실행"):
        with st.spinner("분석 중..."):
            st.session_state['brand_analysis'] = analyze_ai(extract_text(b_f, [b_u]), "brand", st.session_state['brand_insight'])
            _ = st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 분석 (3 Sets)":
    st.title("⚔️ STEP 1.5. 경쟁사 3세트 분석")
    c_f = st.file_uploader("경쟁사 자료 업로드", accept_multiple_files=True)
    col1, col2 = st.columns([1, 2])
    with col1: c1n = st.text_input("경쟁사 1 이름"); c2n = st.text_input("경쟁사 2 이름"); c3n = st.text_input("경쟁사 3 이름")
    with col2: c1u = st.text_input("경쟁사 1 URL"); c2u = st.text_input("경쟁사 2 URL"); c3u = st.text_input("경쟁사 3 URL")
    
    if st.button("경쟁사 분석 실행"):
        with st.spinner("지정 브랜드만 분석 중..."):
            all_c = extract_text(c_f, [c1u, c2u, c3u])
            for n in [c1n, c2n, c3n]:
                if n:
                    res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{n} 마케팅 소구점", "gl": "kr", "hl": "ko"}).json()
                    if 'organic' in res: all_c += f"\n[{n}]\n" + "\n".join([r.get('snippet', '') for r in res['organic']])
            st.session_state['comp_analysis'] = analyze_ai(all_c, "comp", brand_context=st.session_state['brand_analysis'])
            _ = st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 데이터 (Multi-KW)":
    st.title("👥 STEP 2. 멀티 키워드 데이터 수집")
    st.info("쉼표(,)로 키워드를 구분하세요. (예: 스마트카라, 음식물처리기)")
    kw_in = st.text_input("분석 키워드")
    if st.button("데이터 수집 시작"):
        with st.spinner("수집 중..."):
            all_r = []
            keywords = [k.strip() for k in kw_in.split(',')]
            for k in keywords:
                if k:
                    for qs in ["후기", "단점", "실망"]:
                        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{k} {qs}", "num": 10, "gl": "kr", "hl": "ko"}).json()
                        if 'organic' in res: all_r.extend([{'title': r.get('title'), 'body': r.get('snippet')} for r in res['organic']])
            st.session_state['consumer_data'] = all_r
            st.session_state['consumer_analysis'] = analyze_ai(str(all_r), "consumer")
            _ = st.rerun()
    if st.session_state['consumer_analysis']: 
        st.markdown(st.session_state['consumer_analysis'])
        _ = st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 최종 전략 및 PDF":
    st.title("🧠 STEP 3. Victory Strategy 리포트")
    if st.button("🚀 최종 리포트 생성"):
        with st.spinner("데이터 합성 중..."):
            comb = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_ai(comb, "final", st.session_state['brand_insight'], consumer_raw=str(st.session_state['consumer_data']))
            _ = st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        _ = st.divider()
        st.subheader("📥 리포트 다운로드")
        export_list = [("BRAND", st.session_state['brand_analysis']), ("COMPETITOR", st.session_state['comp_analysis']), 
                       ("CONSUMER", st.session_state['consumer_analysis']), ("STRATEGY", st.session_state['final_report'])]
        
        col_pdf, col_txt = st.columns(2)
        with col_pdf:
            try:
                pdf = SafePDF(); _ = pdf.add_page()
                for t, b in export_list:
                    if b:
                        _ = pdf.set_fill_color(240, 240, 240); _ = pdf.set_font(pdf.fn, 'B', 12)
                        _ = pdf.cell(160, 10, txt=f" {t}", ln=True, fill=True); _ = pdf.ln(3)
                        _ = pdf.write_text(b); _ = pdf.ln(8)
                st.download_button("📥 PDF 다운로드", data=bytes(pdf.output()), file_name="Strategy_Report.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"PDF 오류: {e}")
        with col_txt:
            full_txt = ""
            for t, b in export_list: full_txt += f"[{t}]\n{b}\n\n"
            st.download_button("📥 텍스트 파일(.txt) 다운로드", data=full_txt, file_name="Strategy_Report.txt", mime="text/plain")
