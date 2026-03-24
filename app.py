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
st.set_page_config(page_title="GapFinder AI v8.2", layout="wide")

states = ['brand_text', 'brand_insight', 'brand_analysis', 'comp_analysis', 
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
    menu = st.radio("전략 수립 단계", ["STEP 1. 자사 분석", "STEP 1.5. 경쟁사 분석", "STEP 2. 소비자 분석", "STEP 3. 전략 및 통합 PDF"])

# --- 3. 고품격 PDF 엔진 (표 렌더링 기능 추가) ---
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

    def header(self):
        if hasattr(self, 'font_family_k') and self.page_no() == 1:
            self.set_font(self.font_family_k, 'B', 22)
            self.set_text_color(0, 51, 102)
            self.cell(0, 25, "Strategic Gap Analysis Report", ln=True, align='C')
            self.ln(5)

    def write_smart_text(self, text):
        effective_width = self.w - 40 # 여백 고려
        lines = text.split('\n')
        
        table_data = [] # 표 데이터를 임시 저장
        
        for line in lines:
            line = line.strip()
            if not line: self.ln(5); continue
            
            # 1. 마크다운 표 인식 (|...|)
            if line.startswith('|'):
                # 구분선(|---|)은 무시
                if '---' in line: continue
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if cells: table_data.append(cells)
                continue
            
            # 표 데이터가 모였다면 표로 출력하고 비움
            if table_data:
                self.draw_table(table_data)
                table_data = []

            # 2. 헤더 및 본문 처리
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
                self.set_font(self.font_family_k, '', 10.5)
        
        # 마지막 줄이 표인 경우 처리
        if table_data: self.draw_table(table_data)

    def draw_table(self, data):
        """FPDF2의 table 기능을 활용해 깔끔한 표를 그립니다."""
        self.set_font(self.font_family_k, '', 9)
        with self.table(borders_layout="HORIZONTAL_LINES", cell_fill_color=245, cell_fill_mode="ROWS", line_height=8) as t:
            for data_row in data:
                row = t.row()
                for datum in data_row:
                    row.cell(datum)
        self.ln(5)

# --- 4. 분석 엔진 (이전과 동일) ---
def analyze_ai(content, target_type, insight=""):
    client = genai.Client(api_key=gemini_key)
    prompt_base = "당신은 광고 기획자입니다. 자기소개는 생략하고 바로 본론부터 마크다운 형식을 사용하여 작성하세요. 특히 Gap 분석은 표(|구분|브랜드|소비자|Gap|) 형식을 사용하세요.\n\n"
    # (이하 analyze_ai 로직 유지)
    res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt_base + "\n\n데이터:\n" + content[:8000])
    return res.text

# --- 5. 화면 레이아웃 및 다운로드 설정 ---
# (STEP 1, 2 로직 유지)

elif menu == "STEP 3. 전략 및 통합 PDF":
    st.title("🧠 최종 전략 및 통합 리포트")
    # (중략: final_report 생성 로직)
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        st.subheader("📥 리포트 다운로드 설정")
        col1, col2, col3, col4 = st.columns(4)
        with col1: i1 = st.checkbox("자사 분석", value=True)
        with col2: i2 = st.checkbox("경쟁사 분석", value=True)
        with col3: i3 = st.checkbox("소비자 분석", value=True)
        with col4: i4 = st.checkbox("최종 전략", value=True)
        
        if st.button("📑 프리미엄 통합 PDF 생성"):
            export_list = []
            if i1: export_list.append(("BRAND ANALYSIS", st.session_state['brand_analysis']))
            if i2: export_list.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
            if i3: export_list.append(("CONSUMER REAL VOICE", st.session_state['consumer_analysis']))
            if i4: export_list.append(("FINAL STRATEGY", st.session_state['final_report']))
            
            if export_list:
                pdf = ProPDF()
                pdf.add_page()
                for title, body in export_list:
                    if body:
                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_font(pdf.font_family_k, 'B', 15)
                        pdf.cell(0, 15, txt=f" {title}", ln=True, fill=True); pdf.ln(5)
                        pdf.write_smart_text(body); pdf.ln(10)
                st.download_button("📥 고퀄리티 PDF 다운로드", data=bytes(pdf.output()), file_name="Strategy_Master_Report.pdf")
