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
                self.set_font(self
