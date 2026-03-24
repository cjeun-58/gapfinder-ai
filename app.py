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
import re

# --- 1. 기본 설정 및 데이터 초기화 ---
st.set_page_config(page_title="GapFinder AI v8.3", layout="wide")

states = ['brand_text', 'brand_insight', 'brand_analysis', 'comp_text', 'comp_analysis', 
          'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key or 'insight' in key else []

# --- 2. 사이드바 ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 자사 분석 & 인사이트", 
        "STEP 1.5. 경쟁사 분석", 
        "STEP 2. 소비자 분석", 
        "STEP 3. 전략 및 통합 PDF"
    ])
    st.divider()
    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 자사: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 고품격 PDF 엔진 (표 렌더링 포함) ---
class ProPDF(FPDF):
    def __init__(self):
        super().__init__()
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg) and os.path.exists(f_bold):
            self.add_font('NG', '', f_reg)
            self.add_font('NG', 'B', f_bold)
            self.font_family_k = 'NG'
        else: self.font_family_k = 'Arial'
        self.set_auto_page_break(auto=True, margin=20)
        self.l_margin_v = 20
        self.r_margin_v = 20
        self.set_margins(self.l_margin_v, 15, self.r_margin_v)

    def header(self):
        if hasattr(self, 'font_family_k') and self.page_no() == 1:
            self.set_font(self.font_family_k, 'B', 22)
            self.set_text_color(0, 51, 102)
            self.cell(0, 25, "Strategic Gap Analysis Report", ln=True, align='C')
            self.ln(5)

    def write_smart_text(self, text):
        effective_width = self.w - self.l_margin - self.r_margin
        lines = text.split('\n')
        table_data = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if table_data:
                    self.draw_pretty_table(table_data)
                    table_data = []
                self.ln(5)
                continue
            
            if line.startswith('|'):
                if '---' in line: continue
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if cells: table_data.append(cells)
                continue
            
            if table_data:
                self.draw_pretty_table(table_data)
                table_data = []

            if line.startswith('###'):
                self.set_font(self.font_family_k, 'B', 13); self.set_text_color(0, 102, 204)
                self.multi_cell(effective_width, 9, txt=line.replace('###', '').strip()); self.ln(1)
            elif line.startswith('##'):
                self.set_font(self.font_family_k, 'B', 15); self.set_text_color(0, 51, 102)
                self.multi_cell(effective_width, 11, txt=line.replace('##', '').strip()); self.ln(2)
            else:
                self.set_font(self.font_family_k, '', 10.5); self.set_text_color(50, 50, 50)
                if '**' in line:
                    self.set_font(self.font_family_k, 'B', 10.5)
                    line = line.replace('**', '')
                clean_line = re.sub(r'[^\u0000-\u007f\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7af\ud7b0-\ud7ff]', '', line)
                self.multi_cell(effective_width, 7, txt=clean_line)
        if table_data: self.draw_pretty_table(table_data)

    def draw_pretty_table(self, data):
        self.set_font(self.font_family_k, '', 9)
        with self.table(borders_layout="HORIZONTAL_LINES", cell_fill_color=245, cell_fill_mode="ROWS", line_height=8) as t:
            for data_row in data:
                row = t.row()
                for datum in data_row:
                    row.cell(datum)
        self.ln(5)

# --- 4. 분석 엔진 ---
def analyze_ai(content, target_type, insight=""):
    client = genai.Client(api_key=gemini_key)
    prompt_base = "인사말이나 자기소개 없이 바로 본론부터 마크다운(#, ##, **) 형식으로 작성하세요. 특히 Gap 분석은 표(|구분|브랜드|소비자|Gap|) 형식을 사용하세요.\n\n"
    
    if target_type == "brand":
        prompt = f"{prompt_base}브랜드 자료와 [운영 인사이트]를 반영하여 분석하세요.\n인사이트: {insight}"
    elif target_type == "final":
        prompt = f"{prompt_base}자사/경쟁사/소비자 데이터를 대조하여 필승 전략을 도출하세요.\n인사이트: {insight}"
    else:
        prompt = f"{prompt_base}{target_type} 데이터를 심층 분석하세요."
        
    res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt + "\n\n데이터:\n" + content[:8000])
    return res.text

# --- 5. 메인 로직 ---

if menu == "STEP 1. 자사 분석 & 인사이트":
    st.title("🏢 STEP 1. 자사 보이스 및 인사이트 분석")
    files = st.file_uploader("자료 업로드", accept_multiple_files=True)
    url = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 운영 인사이트", value=st.session_state['brand_insight'], height=100)
    
    if st.button("분석 실행"):
        text = ""
        if files:
            for f in files:
                if f.name.endswith(".pdf"): text += "\n".join([p.extract_text() for p in PdfReader(f).pages])
                elif f.name.endswith(".pptx"): text += "\n".join([s.text for slide in Presentation(f).slides for s in slide.shapes if hasattr(s, "text")])
        if url:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            text += BeautifulSoup(res.text, 'html.parser').get_text()[:3000]
        st.session_state['brand_analysis'] = analyze_ai(text + st.session_state['brand_insight'], "brand", st.session_state['brand_insight'])
        st.rerun()
    st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 분석":
    st.title("⚔️ STEP 1.5. 경쟁사 전략 탐색")
    comp_name = st.text_input("경쟁사 브랜드명")
    if st.button("경쟁사 분석 실행"):
        q = f"{comp_name} 특징 소구점 마케팅"
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": q, "gl": "kr", "hl": "ko"}).json()
        comp_info = "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
        st.session_state['comp_analysis'] = analyze_ai(comp_info, "comp")
        st.rerun()
    st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 분석":
    st.title("👥 STEP 2. 소비자 리얼 보이스")
    kw = st.text_input("포함 키워드")
    if st.button("수집 시작"):
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": kw + " 후기", "gl": "kr", "hl": "ko"}).json()
        data = [{'title': r.get('title'), 'body': r.get('snippet')} for r in res.get('organic', [])]
        st.session_state['consumer_data'] = data
        st.session_state['consumer_analysis'] = analyze_ai(str(data), "consumer")
        st.rerun()
    if st.session_state['consumer_analysis']:
        st.markdown(st.session_state['consumer_analysis'])
        st.dataframe(pd.DataFrame(st.session_state['consumer_data']))

elif menu == "STEP 3. 전략 및 통합 PDF":
    st.title("🧠 STEP 3. 최종 전략 및 PDF 추출")
    if st.button("🚀 필승 전략 도출"):
        data = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
        st.session_state['final_report'] = analyze_ai(data, "final", st.session_state['brand_insight'])
        st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        st.subheader("📥 다운로드 설정")
        col1, col2, col3, col4 = st.columns(4)
        with col1: i1 = st.checkbox("자사", value=True)
        with col2: i2 = st.checkbox("경쟁사", value=True)
        with col3: i3 = st.checkbox("소비자", value=True)
        with col4: i4 = st.checkbox("전략", value=True)
        
        if st.button("📑 프리미엄 PDF 생성"):
            export_list = []
            if i1: export_list.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
            if i2: export_list.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
            if i3: export_list.append(("CONSUMER ANALYSIS", st.session_state['consumer_analysis']))
            if i4: export_list.append(("FINAL STRATEGY", st.session_state['final_report']))
            
            pdf = ProPDF()
            pdf.add_page()
            for title, body in export_list:
                if body:
                    pdf.set_fill_color(240, 240, 240); pdf.set_font(pdf.font_family_k, 'B', 15)
                    pdf.cell(0, 15, txt=f" {title}", ln=True, fill=True); pdf.ln(5)
                    pdf.write_smart_text(body); pdf.ln(10)
            st.download_button("📥 PDF 다운로드", data=bytes(pdf.output()), file_name="Total_Strategy_Report.pdf")
