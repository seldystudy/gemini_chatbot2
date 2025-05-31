import streamlit as st
import json
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import google.generativeai as genai
from datetime import datetime, timedelta
import tempfile
import os
import pdfplumber
from docx import Document
import olefile
import re
import urllib.parse
from fpdf import FPDF
import io
import base64

# 페이지 설정
st.set_page_config(
    page_title="지원사업 플랫폼",
    page_icon="��",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 스테이트 초기화
def initialize_session_state():
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    if 'sites' not in st.session_state:
        st.session_state.sites = []
    if 'show_add_site_modal' not in st.session_state:
        st.session_state.show_add_site_modal = False
    if 'edit_site_index' not in st.session_state:
        st.session_state.edit_site_index = None
    if 'announcements' not in st.session_state:
        st.session_state.announcements = []
    if 'analyzed_files' not in st.session_state:
        st.session_state.analyzed_files = {}
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()
    if 'company_info' not in st.session_state:
        st.session_state.company_info = {
            'name': '',
            'established_year': '',
            'industry': '',
            'company_type': '',
            'employee_count': '',
            'revenue': '',
            'stage': '',
            'region': '',
            'address': '',
            'business_areas': []
        }
    if 'recommended_announcements' not in st.session_state:
        st.session_state.recommended_announcements = []
    if 'update_cycle' not in st.session_state:
        st.session_state.update_cycle = '수동'
    if 'last_update' not in st.session_state:
        st.session_state.last_update = None

initialize_session_state()

# Gemini API 설정
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")
except Exception as e:
    st.error("Gemini API 키 설정에 실패했습니다. .streamlit/secrets.toml 파일을 확인해주세요.")

# CSS 스타일 정의
def get_css():
    return """
<style>
    /* 전체 앱 스타일 */
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* 헤더 스타일 */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 2rem;
        margin-bottom: 2rem;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* 공고 카드 스타일 */
    .announcement-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
    }
    
    .announcement-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .announcement-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 1rem;
        padding-right: 2rem;
    }
    
    .announcement-info {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1rem;
    }
    
    .info-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .info-label {
        color: #888;
        font-size: 0.9rem;
    }
    
    .favorite-btn {
        position: absolute;
        top: 1rem;
        right: 1rem;
        cursor: pointer;
        font-size: 1.5rem;
        color: #ff4b4b;
        transition: transform 0.2s ease;
    }
    
    .favorite-btn:hover {
        transform: scale(1.2);
    }
    
    .card-actions {
        display: flex;
        gap: 1rem;
        margin-top: 1rem;
        justify-content: flex-end;
    }
    
    .action-btn {
        padding: 0.5rem 1rem;
        border-radius: 5px;
        font-size: 0.9rem;
        cursor: pointer;
        transition: background-color 0.2s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .action-btn:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }
    
    .pdf-btn {
        color: #ff4b4b;
    }
    
    .excel-btn {
        color: #4CAF50;
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        border-radius: 10px;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.1);
    }
    
    /* 버튼 스타일 */
    .stButton button {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    /* 사이드바 스타일 */
    .css-1d391kg {
        padding: 2rem 1rem;
    }
    
    /* 인포그래픽 카드 */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 1rem;
        color: #888;
    }
    
    /* 파일 분석 결과 */
    .file-analysis-result {
        background: rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 1rem;
    }
    
    /* 다크모드 토글 */
    .dark-mode-toggle {
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 1000;
    }
    
    /* 공고 목록과 상세 보기 레이아웃 */
    .announcements-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        height: calc(100vh - 200px);
        overflow: hidden;
    }
    
    .announcements-list {
        overflow-y: auto;
        padding-right: 1rem;
    }
    
    .announcement-detail {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 2rem;
        height: 100%;
        overflow-y: auto;
        position: relative;
    }
    
    .detail-header {
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .detail-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    
    .detail-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin-bottom: 1rem;
    }
    
    .detail-content {
        margin-bottom: 2rem;
        line-height: 1.6;
    }
    
    /* 첨부파일 스타일 */
    .attachments-list {
        margin-top: 2rem;
    }
    
    .attachment-item {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        cursor: pointer;
        transition: background-color 0.2s ease;
    }
    
    .attachment-item:hover {
        background: rgba(255, 255, 255, 0.1);
    }
    
    .attachment-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .attachment-title {
        font-weight: bold;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .attachment-preview {
        margin-top: 1rem;
        padding: 1rem;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 8px;
        font-size: 0.9rem;
    }
    
    .preview-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .preview-content {
        max-height: 200px;
        overflow-y: auto;
        padding-right: 1rem;
    }
    
    .expand-btn {
        color: #888;
        cursor: pointer;
        font-size: 0.9rem;
        text-decoration: underline;
    }
    
    /* 회사 정보 폼 스타일 */
    .company-info-form {
        background: rgba(255, 255, 255, 0.05);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    
    .form-section {
        margin-bottom: 1.5rem;
    }
    
    .form-section-title {
        font-size: 1.1rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #4CAF50;
    }
    
    /* 추천 공고 카드 스타일 */
    .recommended-card {
        background: linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(76, 175, 80, 0.05) 100%);
        border: 1px solid rgba(76, 175, 80, 0.2);
        position: relative;
    }
    
    .recommendation-badge {
        position: absolute;
        top: -10px;
        right: -10px;
        background: #4CAF50;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    .match-score {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0.5rem;
        color: #4CAF50;
        font-weight: bold;
    }
    
    .match-score-bar {
        height: 4px;
        background: rgba(76, 175, 80, 0.2);
        border-radius: 2px;
        overflow: hidden;
    }
    
    .match-score-fill {
        height: 100%;
        background: #4CAF50;
        transition: width 0.3s ease;
    }
    
    /* 사이트 관리 테이블 스타일 */
    .sites-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        overflow: hidden;
    }
    
    .sites-table th {
        background: rgba(0, 0, 0, 0.2);
        padding: 1rem;
        text-align: left;
        font-weight: 500;
    }
    
    .sites-table td {
        padding: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .sites-table tr:hover {
        background: rgba(255, 255, 255, 0.05);
    }
    
    /* 모달 스타일 */
    .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
        z-index: 1000;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .modal-content {
        background: var(--background-color);
        padding: 2rem;
        border-radius: 15px;
        width: 90%;
        max-width: 600px;
        box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
    }
    
    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
    }
    
    .modal-title {
        font-size: 1.2rem;
        font-weight: bold;
    }
    
    .modal-close {
        cursor: pointer;
        font-size: 1.5rem;
        color: #888;
    }
    
    /* 토글 스위치 스타일 */
    .toggle-switch {
        position: relative;
        display: inline-block;
        width: 50px;
        height: 24px;
    }
    
    .toggle-switch input {
        opacity: 0;
        width: 0;
        height: 0;
    }
    
    .toggle-slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #ccc;
        transition: .4s;
        border-radius: 24px;
    }
    
    .toggle-slider:before {
        position: absolute;
        content: "";
        height: 16px;
        width: 16px;
        left: 4px;
        bottom: 4px;
        background-color: white;
        transition: .4s;
        border-radius: 50%;
    }
    
    input:checked + .toggle-slider {
        background-color: #4CAF50;
    }
    
    input:checked + .toggle-slider:before {
        transform: translateX(26px);
    }
    
    /* 버튼 스타일 */
    .site-action-btn {
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        cursor: pointer;
        font-size: 0.9rem;
        transition: background-color 0.2s ease;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .edit-btn {
        background: rgba(33, 150, 243, 0.1);
        color: #2196F3;
    }
    
    .delete-btn {
        background: rgba(244, 67, 54, 0.1);
        color: #F44336;
    }
    
    .add-site-btn {
        background: #4CAF50;
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 8px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        width: fit-content;
    }
</style>
""" + (".dark-mode {}" if st.session_state.get('dark_mode', False) else "")

# PDF 생성 함수
def create_announcement_pdf(announcement):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    
    # 제목
    pdf.cell(200, 10, txt=announcement['title'], ln=True, align='C')
    pdf.ln(10)
    
    # 요약 정보
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"요약: {announcement['summary']}")
    pdf.multi_cell(0, 10, f"분류: {announcement['category']}")
    if 'suitability' in announcement:
        pdf.multi_cell(0, 10, f"적합도: {announcement['suitability']}")
    pdf.multi_cell(0, 10, f"원문 링크: {announcement['url']}")
    
    return pdf

# 엑셀 생성 함수
def create_excel():
    df = pd.DataFrame(st.session_state.announcements)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def extract_text_from_pdf(file_path):
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"PDF 파일 처리 중 오류가 발생했습니다: {str(e)}")
        return None

def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        return " ".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        st.error(f"DOCX 파일 처리 중 오류가 발생했습니다: {str(e)}")
        return None

def extract_text_from_hwp(file_path):
    try:
        import subprocess
        result = subprocess.run(['hwp5txt', file_path], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            st.warning("HWP 파일 변환에 실패했습니다. 시스템에 hwp5txt가 설치되어 있는지 확인해주세요.")
            return None
    except Exception as e:
        st.error(f"HWP 파일 처리 중 오류가 발생했습니다: {str(e)}")
        return None

def analyze_file_content(file_url, announcement_title):
    if file_url in st.session_state.analyzed_files:
        return st.session_state.analyzed_files[file_url]
    
    try:
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            # 파일 다운로드
            response = requests.get(file_url, headers={'User-Agent': 'Mozilla/5.0'})
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name

        # 파일 확장자 확인
        file_ext = os.path.splitext(file_url)[1].lower()
        
        # 파일 형식에 따른 텍스트 추출
        if file_ext == '.pdf':
            text = extract_text_from_pdf(tmp_file_path)
        elif file_ext == '.docx':
            text = extract_text_from_docx(tmp_file_path)
        elif file_ext == '.hwp':
            text = extract_text_from_hwp(tmp_file_path)
        else:
            st.error(f"지원되지 않는 파일 형식입니다: {file_ext}")
            return None

        # 임시 파일 삭제
        os.unlink(tmp_file_path)

        if text:
            # Gemini API로 텍스트 분석
            prompt = f"""다음은 정부 지원사업의 첨부문서입니다.
            이 내용을 읽고 1문단으로 요약하고, 다음 중 어떤 지원사업 유형인지 분류해줘:
            ①창업지원 ②기술개발(R&D) ③마케팅지원 ④해외진출 ⑤시설·장비지원 ⑥인건비지원 ⑦기타

            공고 제목: {announcement_title}
            문서 내용:
            {text[:8000]}  # 텍스트가 너무 길면 앞부분만 사용
            """
            
            response = model.generate_content(prompt)
            analysis = response.text
            
            # 분석 결과 파싱
            parts = analysis.split('분류:') if '분류:' in analysis else [analysis, "미분류"]
            summary = parts[0].strip()
            category = parts[1].strip() if len(parts) > 1 else "미분류"
            
            result = {
                'summary': summary,
                'category': category
            }
            
            # 결과 캐시
            st.session_state.analyzed_files[file_url] = result
            return result
            
    except Exception as e:
        st.error(f"파일 분석 중 오류가 발생했습니다: {str(e)}")
        return None

def find_attachment_links(soup, base_url):
    attachments = []
    for link in soup.find_all('a'):
        href = link.get('href', '')
        if href:
            # 상대 URL을 절대 URL로 변환
            if not href.startswith(('http://', 'https://')):
                href = urllib.parse.urljoin(base_url, href)
            
            # 지원하는 파일 확장자 체크
            if re.search(r'\.(pdf|docx|hwp)$', href.lower()):
                attachments.append({
                    'url': href,
                    'name': link.get_text().strip() or os.path.basename(href)
                })
    return attachments

# 공고 수집 및 분석 함수
def crawl_and_analyze():
    new_announcements = []
    
    for site in st.session_state.sites:
        try:
            response = requests.get(site['url'], headers={'User-Agent': 'Mozilla/5.0'})
            soup = bs(response.text, 'html.parser')
            
            links = soup.find_all('a')
            for link in links:
                href = link.get('href')
                title = link.get_text().strip()
                
                if href and title and len(title) > 5:
                    if href.startswith('/'):
                        href = site['url'] + href
                    elif not href.startswith('http'):
                        continue
                    
                    try:
                        page_response = requests.get(href, headers={'User-Agent': 'Mozilla/5.0'})
                        page_soup = bs(page_response.text, 'html.parser')
                        attachments = find_attachment_links(page_soup, href)
                    except:
                        attachments = []
                    
                    # Gemini API로 텍스트 분석 및 회사 적합도 평가
                    company_info = st.session_state.company_info
                    prompt = f"""다음은 정부 지원사업 공고입니다. 

1. 이 공고를 한 문단으로 요약하고,
2. 다음 중 어떤 유형인지 분류해줘: ①창업지원 ②기술개발(R&D) ③마케팅지원 ④해외진출 ⑤시설·장비지원 ⑥인건비지원 ⑦기타

또한, 우리 회사는 다음과 같습니다:
- 업종: {company_info['industry']}
- 매출 규모: {company_info['revenue']}
- 단계: {company_info['stage']}
- 지역: {company_info['region']}

이 회사에 이 공고가 적합한지 여부를 "매우 적합 / 보통 / 부적합" 중 하나로 평가하고, 이유를 한 문장으로 설명해줘.

제목: {title}
링크: {href}
"""
                    
                    try:
                        response = model.generate_content(prompt)
                        analysis = response.text
                        
                        # 분석 결과 파싱
                        parts = analysis.split('\n\n')
                        summary = parts[0].strip()
                        category = parts[1].strip() if len(parts) > 1 else "미분류"
                        suitability = parts[2].strip() if len(parts) > 2 else "평가 불가"
                        
                        new_announcements.append({
                            'title': title,
                            'summary': summary[:100] + '...' if len(summary) > 100 else summary,
                            'full_summary': summary,
                            'category': category,
                            'suitability': suitability,
                            'url': href,
                            'site_name': site['name'],
                            'date': datetime.now().strftime("%Y-%m-%d"),
                            'attachments': attachments
                        })
                    except Exception as e:
                        st.warning(f"텍스트 분석 중 오류 발생: {str(e)}")
                        continue
                        
        except Exception as e:
            st.error(f"{site['name']} 크롤링 중 오류 발생: {str(e)}")
            continue
    
    return new_announcements

# 업데이트 주기 체크
def check_update_needed():
    if st.session_state.last_update is None:
        return True
    
    last_update = st.session_state.last_update
    current_time = datetime.now()
    
    if st.session_state.update_cycle == '매일':
        return (current_time - last_update).days >= 1
    elif st.session_state.update_cycle == '매주':
        return (current_time - last_update).days >= 7
    return False

# 헤더 섹션
def render_header():
    st.markdown("""
        <div class="header-container">
            <h1>지원사업 플랫폼 🎯</h1>
            <div class="dark-mode-toggle">
                <span>🌙</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # 다크모드 토글 (헤더 오른쪽)
    if st.toggle("다크모드", value=st.session_state.dark_mode, key="dark_mode_toggle"):
        st.session_state.dark_mode = True
        st.markdown("""
            <style>
                .stApp {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.session_state.dark_mode = False

# 메인 대시보드
def render_dashboard():
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">등록된 사이트</div>
                <div class="metric-value">{len(st.session_state.sites)}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">수집된 공고</div>
                <div class="metric-value">{len(st.session_state.announcements)}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">즐겨찾기</div>
                <div class="metric-value">{len(st.session_state.favorites)}</div>
            </div>
        """, unsafe_allow_html=True)

# 사이트 관리 모달
def render_site_modal():
    with st.form("site_modal_form", clear_on_submit=True):  # form key를 고유하게 변경
        st.subheader("새 사이트 추가" if not st.session_state.edit_site_index else "사이트 수정")
        
        site_data = st.session_state.sites[st.session_state.edit_site_index] if st.session_state.edit_site_index is not None else None
        
        site_name = st.text_input("사이트 이름", value=site_data['name'] if site_data else "")
        site_url = st.text_input("사이트 URL", value=site_data['url'] if site_data else "")
        
        col1, col2 = st.columns(2)
        with col1:
            auto_collect = st.checkbox("자동 수집 사용", value=site_data.get('auto_collect', False) if site_data else False)
        
        with col2:
            collect_cycle = st.selectbox(
                "수집 주기",
                ["매일", "매주", "매월"],
                index=["매일", "매주", "매월"].index(site_data.get('collect_cycle', '매일')) if site_data and site_data.get('collect_cycle') else 0,
                disabled=not auto_collect
            )
        
        col3, col4 = st.columns([1, 1])
        with col3:
            submit = st.form_submit_button("저장", use_container_width=True)
        with col4:
            if st.form_submit_button("취소", use_container_width=True):
                st.session_state.show_add_site_modal = False
                st.rerun()
        
        if submit and site_name and site_url:
            if st.session_state.edit_site_index is not None:
                st.session_state.sites[st.session_state.edit_site_index] = {
                    'name': site_name,
                    'url': site_url,
                    'auto_collect': auto_collect,
                    'collect_cycle': collect_cycle if auto_collect else None
                }
                st.success(f"'{site_name}' 사이트가 수정되었습니다!")
            else:
                if not any(site['name'] == site_name for site in st.session_state.sites):
                    st.session_state.sites.append({
                        'name': site_name,
                        'url': site_url,
                        'auto_collect': auto_collect,
                        'collect_cycle': collect_cycle if auto_collect else None
                    })
                    st.success(f"'{site_name}' 사이트가 추가되었습니다!")
                else:
                    st.error("이미 존재하는 사이트 이름입니다!")
            
            st.session_state.show_add_site_modal = False
            st.rerun()

# 사이트 관리 탭
def render_sites_tab():
    st.markdown("""
        <h3 style="margin-bottom: 2rem;">📋 지원사업 사이트 관리</h3>
    """, unsafe_allow_html=True)
    
    # 사이트 추가 버튼
    if st.button("➕ 새 사이트 추가", key="add_site_btn", help="새로운 지원사업 사이트를 추가합니다"):
        st.session_state.show_add_site_modal = True
        st.session_state.edit_site_index = None
    
    # 모달 표시
    if st.session_state.show_add_site_modal:
        render_site_modal()
    
    # 사이트 목록 테이블
    if st.session_state.sites:
        for idx, site in enumerate(st.session_state.sites):
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{site['name']}**")
                    st.write(f"URL: {site['url']}")
                with col2:
                    st.write("자동 수집:", "✅" if site.get('auto_collect') else "❌")
                    if site.get('auto_collect'):
                        st.write("주기:", site.get('collect_cycle', '-'))
                with col3:
                    if st.button("수정", key=f"edit_site_{idx}"):
                        st.session_state.show_add_site_modal = True
                        st.session_state.edit_site_index = idx
                        st.rerun()
                    if st.button("삭제", key=f"delete_site_{idx}"):
                        if st.session_state.sites:
                            st.session_state.sites.pop(idx)
                            st.rerun()
                st.markdown("---")
    else:
        st.info("등록된 사이트가 없습니다. '새 사이트 추가' 버튼을 눌러 사이트를 추가해보세요.")

# 공고 목록 탭
def render_announcements_tab():
    if not st.session_state.announcements:
        st.info("수집된 공고가 없습니다. '공고 수집하기' 버튼을 눌러 새로운 공고를 수집해보세요.")
        return
    
    # 필터 옵션
    col1, col2, col3 = st.columns(3)
    with col1:
        category_filter = st.selectbox(
            "지원 유형",
            ["전체"] + list(set(ann['category'] for ann in st.session_state.announcements))
        )
    with col2:
        site_filter = st.selectbox(
            "기관",
            ["전체"] + list(set(ann['site_name'] for ann in st.session_state.announcements))
        )
    with col3:
        suitability_filter = st.selectbox(
            "적합도",
            ["전체", "매우 적합", "보통", "부적합"]
        )
    
    # 필터링된 공고 목록
    filtered_announcements = st.session_state.announcements
    if category_filter != "전체":
        filtered_announcements = [ann for ann in filtered_announcements if ann['category'] == category_filter]
    if site_filter != "전체":
        filtered_announcements = [ann for ann in filtered_announcements if ann['site_name'] == site_filter]
    if suitability_filter != "전체":
        filtered_announcements = [ann for ann in filtered_announcements if suitability_filter in ann.get('suitability', '')]
    
    # 선택된 공고 상태 관리
    if 'selected_announcement' not in st.session_state:
        st.session_state.selected_announcement = None
    if 'expanded_attachments' not in st.session_state:
        st.session_state.expanded_attachments = set()
    
    # 엑셀 다운로드 버튼
    col1, col2 = st.columns([8, 2])
    with col2:
        excel_data = create_excel()
        st.download_button(
            label="📊 전체 목록 다운로드",
            data=excel_data,
            file_name="지원사업_목록.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # 공고 목록과 상세 보기 컨테이너
    st.markdown('<div class="announcements-container">', unsafe_allow_html=True)
    
    # 왼쪽: 공고 목록
    st.markdown('<div class="announcements-list">', unsafe_allow_html=True)
    for idx, announcement in enumerate(filtered_announcements):
        is_selected = st.session_state.selected_announcement == announcement['title']
        
        # URL 처리
        url_display = announcement.get('url', '')
        if url_display and len(url_display) > 50:
            url_display = url_display[:47] + "..."
        
        st.markdown(f"""
            <div class="announcement-card" onclick="handleAnnouncementClick('{announcement['title']}')" style="cursor: pointer; {
                'border: 2px solid #4CAF50;' if is_selected else ''
            }">
                <div class="announcement-title">{announcement['title']}</div>
                <div class="favorite-btn">
                    {"❤️" if announcement['title'] in st.session_state.favorites else "🤍"}
                </div>
                <div class="announcement-info">
                    <div class="info-item">
                        <span class="info-label">기관:</span>
                        <span>{announcement['site_name']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">지원유형:</span>
                        <span>{announcement['category']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">URL:</span>
                        <a href="{announcement.get('url', '#')}" target="_blank" style="color: #4CAF50; text-decoration: none;">
                            {url_display if url_display else '링크 없음'}
                        </a>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 공고 선택 버튼 (숨김 처리)
        if st.button("선택", key=f"select_{idx}", help="공고 상세 보기"):
            st.session_state.selected_announcement = announcement['title']
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 오른쪽: 상세 보기
    st.markdown('<div class="announcement-detail">', unsafe_allow_html=True)
    if st.session_state.selected_announcement:
        selected = next(ann for ann in filtered_announcements if ann['title'] == st.session_state.selected_announcement)
        
        # 상세 정보 헤더
        st.markdown(f"""
            <div class="detail-header">
                <div class="detail-title">{selected['title']}</div>
                <div class="detail-meta">
                    <div class="info-item">
                        <span class="info-label">기관:</span>
                        <span>{selected['site_name']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">지원유형:</span>
                        <span>{selected['category']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">적합도:</span>
                        <span>{selected.get('suitability', '평가 없음')}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">등록일:</span>
                        <span>{selected['date']}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 본문 내용
        st.markdown(f"""
            <div class="detail-content">
                <h4>공고 요약</h4>
                <p>{selected['full_summary']}</p>
                <div style="margin-top: 1rem;">
                    <a href="{selected['url']}" target="_blank" class="action-btn">
                        🔗 원문 보기
                    </a>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 첨부파일 목록
        if selected.get('attachments'):
            st.markdown('<div class="attachments-list">', unsafe_allow_html=True)
            st.markdown('<h4>첨부파일</h4>', unsafe_allow_html=True)
            
            for attachment in selected['attachments']:
                with st.expander(f"📎 {attachment['name']}", expanded=attachment['url'] in st.session_state.expanded_attachments):
                    if st.button("분석하기", key=f"analyze_{attachment['url']}"):
                        with st.spinner("파일을 분석하는 중입니다..."):
                            result = analyze_file_content(attachment['url'], selected['title'])
                            if result:
                                st.markdown(f"""
                                    <div class="attachment-preview">
                                        <div class="preview-header">
                                            <strong>분석 결과</strong>
                                        </div>
                                        <div class="preview-content">
                                            <p><strong>요약:</strong> {result['summary']}</p>
                                            <p><strong>분류:</strong> {result['category']}</p>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                # 상세 분석 결과
                                if st.button("자세히 보기", key=f"detail_{attachment['url']}"):
                                    st.markdown(f"""
                                        <div class="attachment-preview">
                                            <div class="preview-content">
                                                {result.get('detailed_analysis', '상세 분석 결과가 없습니다.')}
                                            </div>
                                        </div>
                                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="text-align: center; color: #888; margin-top: 2rem;">
                👈 왼쪽에서 공고를 선택하면 상세 내용이 여기에 표시됩니다.
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # JavaScript 코드 추가
    st.markdown("""
        <script>
        function handleAnnouncementClick(title) {
            // Streamlit에 이벤트 전달
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: title
            }, '*');
        }
        </script>
    """, unsafe_allow_html=True)

# 상세 정보 탭
def render_details_tab():
    if not st.session_state.announcements:
        st.info("수집된 공고가 없습니다.")
        return
    
    selected_announcement = st.selectbox(
        "공고 선택",
        options=[ann['title'] for ann in st.session_state.announcements],
        format_func=lambda x: x
    )
    
    if selected_announcement:
        announcement = next(ann for ann in st.session_state.announcements if ann['title'] == selected_announcement)
        
        st.markdown(f"""
            <div class="card">
                <h2>{announcement['title']}</h2>
                <p><strong>전체 요약:</strong> {announcement['full_summary']}</p>
                <p><strong>분류:</strong> {announcement['category']}</p>
                <p><strong>적합도:</strong> {announcement.get('suitability', '평가 없음')}</p>
                <p><strong>원문 링크:</strong> <a href="{announcement['url']}" target="_blank">{announcement['url']}</a></p>
            </div>
        """, unsafe_allow_html=True)
        
        if announcement.get('attachments'):
            st.markdown("<h3>첨부파일</h3>", unsafe_allow_html=True)
            for attachment in announcement['attachments']:
                with st.expander(f"📎 {attachment['name']}"):
                    if st.button("파일 분석", key=f"analyze_{attachment['url']}"):
                        with st.spinner("파일을 분석하는 중입니다..."):
                            try:
                                result = analyze_file_content(attachment['url'], announcement['title'])
                                if result:
                                    st.markdown(f"""
                                        <div class="file-analysis-result">
                                            <h4>파일 분석 결과</h4>
                                            <p><strong>요약:</strong> {result['summary']}</p>
                                            <p><strong>분류:</strong> {result['category']}</p>
                                        </div>
                                    """, unsafe_allow_html=True)
                            except Exception as e:
                                st.error("파일 분석에 실패했습니다. 파일 형식이 지원되는지 확인해주세요.")

# 회사 정보 입력 폼
def render_company_info_form(form_key="sidebar_company_info_form"):
    st.markdown("""
        <div class="company-info-form">
            <h3>🏢 내 회사 정보</h3>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form(form_key, clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="form-section">', unsafe_allow_html=True)
            st.markdown('<div class="form-section-title">기본 정보</div>', unsafe_allow_html=True)
            company_name = st.text_input("회사명", value=st.session_state.company_info['name'])
            established_year = st.number_input("설립연도", min_value=1900, max_value=2024, value=int(st.session_state.company_info['established_year']) if st.session_state.company_info['established_year'] else 2024)
            industry = st.selectbox(
                "업종",
                ["", "제조업", "IT/소프트웨어", "서비스업", "도소매업", "건설업", "기타"],
                index=0 if not st.session_state.company_info['industry'] else 
                      ["", "제조업", "IT/소프트웨어", "서비스업", "도소매업", "건설업", "기타"].index(st.session_state.company_info['industry'])
            )
            company_type = st.selectbox(
                "기업형태",
                ["", "개인사업자", "법인사업자", "예비창업자", "소상공인", "중소기업", "중견기업"],
                index=0 if not st.session_state.company_info['company_type'] else
                      ["", "개인사업자", "법인사업자", "예비창업자", "소상공인", "중소기업", "중견기업"].index(st.session_state.company_info['company_type'])
            )
        
        with col2:
            st.markdown('<div class="form-section">', unsafe_allow_html=True)
            st.markdown('<div class="form-section-title">규모 정보</div>', unsafe_allow_html=True)
            employee_count = st.selectbox(
                "직원 수",
                ["", "1-5명", "6-10명", "11-30명", "31-50명", "51-100명", "101명 이상"],
                index=0 if not st.session_state.company_info['employee_count'] else
                      ["", "1-5명", "6-10명", "11-30명", "31-50명", "51-100명", "101명 이상"].index(st.session_state.company_info['employee_count'])
            )
            revenue = st.selectbox(
                "매출 규모",
                ["", "5억 미만", "5억-10억", "10억-30억", "30억-50억", "50억 이상"],
                index=0 if not st.session_state.company_info['revenue'] else
                      ["", "5억 미만", "5억-10억", "10억-30억", "30억-50억", "50억 이상"].index(st.session_state.company_info['revenue'])
            )
            stage = st.selectbox(
                "기업 단계",
                ["", "예비창업", "초기창업", "성장기업", "성숙기업"],
                index=0 if not st.session_state.company_info['stage'] else
                      ["", "예비창업", "초기창업", "성장기업", "성숙기업"].index(st.session_state.company_info['stage'])
            )
        
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">위치 정보</div>', unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            region = st.selectbox(
                "지역",
                ["", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"],
                index=0 if not st.session_state.company_info['region'] else
                      ["", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"].index(st.session_state.company_info['region'])
            )
        with col4:
            address = st.text_input("상세주소", value=st.session_state.company_info['address'])
        
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">사업 분야</div>', unsafe_allow_html=True)
        business_areas = st.multiselect(
            "주요 사업 분야 (복수 선택 가능)",
            ["AI/빅데이터", "IoT", "클라우드", "모바일", "보안", "블록체인", "커머스", "핀테크", "헬스케어", "교육", "콘텐츠", "게임", "로봇", "자율주행", "신재생에너지"],
            default=st.session_state.company_info['business_areas']
        )
        
        if st.form_submit_button("저장", use_container_width=True):
            st.session_state.company_info.update({
                'name': company_name,
                'established_year': str(established_year),
                'industry': industry,
                'company_type': company_type,
                'employee_count': employee_count,
                'revenue': revenue,
                'stage': stage,
                'region': region,
                'address': address,
                'business_areas': business_areas
            })
            st.success("회사 정보가 저장되었습니다!")
            # 추천 공고 업데이트
            update_recommended_announcements()

# 추천 공고 업데이트 함수
def update_recommended_announcements():
    if not st.session_state.announcements:
        return
    
    recommended = []
    company_info = st.session_state.company_info
    
    for announcement in st.session_state.announcements:
        score = 0
        reasons = []
        
        # 지역 매칭
        if company_info['region'] and company_info['region'] in announcement.get('target_regions', [company_info['region']]):
            score += 30
            reasons.append(f"지역 조건 만족 ({company_info['region']})")
        
        # 기업 규모 매칭
        if company_info['company_type'] and company_info['company_type'] in announcement.get('target_companies', [company_info['company_type']]):
            score += 25
            reasons.append(f"기업 규모 적합 ({company_info['company_type']})")
        
        # 업종 매칭
        if company_info['industry'] and company_info['industry'] in announcement.get('target_industries', [company_info['industry']]):
            score += 20
            reasons.append(f"업종 조건 적합 ({company_info['industry']})")
        
        # 사업 분야 매칭
        matching_areas = set(company_info['business_areas']) & set(announcement.get('target_areas', []))
        if matching_areas:
            score += len(matching_areas) * 5
            reasons.append(f"사업 분야 매칭 ({', '.join(matching_areas)})")
        
        if score >= 30:  # 최소 매칭 점수
            recommended.append({
                **announcement,
                'match_score': score,
                'match_reasons': reasons
            })
    
    # 매칭 점수 기준으로 정렬
    recommended.sort(key=lambda x: x['match_score'], reverse=True)
    st.session_state.recommended_announcements = recommended

# 추천 공고 탭
def render_recommended_tab():
    if not st.session_state.recommended_announcements:
        st.info("맞춤 추천을 받으려면 먼저 회사 정보를 입력해주세요.")
        return
    
    st.markdown("""
        <h3 style="margin-bottom: 2rem;">🎯 맞춤 추천 공고</h3>
    """, unsafe_allow_html=True)
    
    for announcement in st.session_state.recommended_announcements:
        match_score = announcement['match_score']
        match_reasons = announcement['match_reasons']
        
        st.markdown(f"""
            <div class="announcement-card recommended-card">
                <div class="recommendation-badge">내게 맞는 공고</div>
                <div class="announcement-title">{announcement['title']}</div>
                <div class="favorite-btn">
                    {"❤️" if announcement['title'] in st.session_state.favorites else "🤍"}
                </div>
                <div class="announcement-info">
                    <div class="info-item">
                        <span class="info-label">기관:</span>
                        <span>{announcement['site_name']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">지원유형:</span>
                        <span>{announcement['category']}</span>
                    </div>
                </div>
                <div class="match-score">
                    <span>매칭 점수: {match_score}%</span>
                    <div class="match-score-bar" style="width: 100px;">
                        <div class="match-score-fill" style="width: {match_score}%;"></div>
                    </div>
                </div>
                <p style="margin-top: 0.5rem;"><strong>추천 이유:</strong> {' / '.join(match_reasons)}</p>
            </div>
        """, unsafe_allow_html=True)

def analyze_announcements_text(text):
    """긴 텍스트에서 공고들을 추출하고 분석하는 함수"""
    try:
        analyzed_announcements = []
        
        # 카테고리별로 공고 분리
        categories = {}
        current_category = None
        current_announcements = []
        current_announcement = None
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            # 대분류 카테고리 확인
            if line.startswith('[') and line.endswith(']'):
                # 이전 카테고리의 마지막 공고 처리
                if current_announcement:
                    current_announcements.append(current_announcement)
                    current_announcement = None
                
                # 이전 카테고리 처리
                if current_category and current_announcements:
                    categories[current_category] = current_announcements
                
                current_category = line.strip('[]')
                current_announcements = []
                continue
            
            # 기관명으로 새로운 공고 시작 확인
            agency_match = re.search(r'\[(.*?)\]', line)
            if agency_match:
                # 이전 공고 처리
                if current_announcement:
                    current_announcements.append(current_announcement)
                
                agency = agency_match.group(1)
                title = line[:line.find('[')].strip()
                
                current_announcement = {
                    'site_name': agency,
                    'title': title,
                    'period': '',
                    'url': '',
                    'details': []
                }
                continue
            
            # 접수기간 확인
            if '접수기간' in line or '신청기간' in line:
                if current_announcement:
                    current_announcement['period'] = line.split(':')[-1].strip()
                continue
            
            # URL 확인
            if line.startswith(('http://', 'https://')):
                if current_announcement:
                    current_announcement['url'] = line.strip()
                continue
            
            # 기타 상세 정보 저장
            if current_announcement:
                current_announcement['details'].append(line)
        
        # 마지막 공고와 카테고리 처리
        if current_announcement:
            current_announcements.append(current_announcement)
        if current_category and current_announcements:
            categories[current_category] = current_announcements
        
        # 각 공고 분석
        for category, announcements in categories.items():
            for ann in announcements:
                if not ann.get('title') or not ann.get('site_name'):
                    continue
                
                try:
                    # Gemini API를 사용한 공고 분석
                    details_text = '\n'.join(ann.get('details', []))
                    prompt = f"""다음 지원사업 공고를 분석하여 아래 정보를 추출해주세요:
                    1. 공고 내용 요약 (1-2문장)
                    2. 지원유형 분류 (①창업지원 ②기술개발(R&D) ③마케팅지원 ④해외진출 ⑤시설·장비지원 ⑥인건비지원 ⑦기타)
                    3. 지원대상 기업 유형
                    4. 예상 지원규모

                    [공고 정보]
                    제목: {ann['title']}
                    기관: {ann['site_name']}
                    접수기간: {ann.get('period', '미지정')}
                    분류: {category}
                    상세내용: {details_text}
                    """
                    
                    response = model.generate_content(prompt)
                    analysis = response.text
                    
                    # 분석 결과 파싱
                    summary = ""
                    support_type = ""
                    target_companies = ""
                    support_scale = ""
                    
                    for line in analysis.split('\n'):
                        line = line.strip()
                        if '요약:' in line:
                            summary = line.split('요약:')[1].strip()
                        elif '지원유형:' in line:
                            support_type = line.split('지원유형:')[1].strip()
                        elif '지원대상:' in line:
                            target_companies = line.split('지원대상:')[1].strip()
                        elif '지원규모:' in line:
                            support_scale = line.split('지원규모:')[1].strip()
                    
                    analyzed_announcements.append({
                        'title': ann['title'],
                        'site_name': ann['site_name'],
                        'period': ann.get('period', '미지정'),
                        'url': ann.get('url', ''),
                        'category': support_type or category,
                        'summary': summary,
                        'target_companies': target_companies,
                        'support_scale': support_scale,
                        'original_category': category
                    })
                    
                except Exception as e:
                    st.warning(f"공고 분석 중 오류 발생: {str(e)}\n제목: {ann.get('title', '제목 없음')}")
                    continue
        
        if not analyzed_announcements:
            st.warning("분석된 공고가 없습니다. 입력 텍스트를 확인해주세요.")
            return []
        
        return analyzed_announcements
        
    except Exception as e:
        st.error(f"텍스트 분석 중 오류가 발생했습니다: {str(e)}")
        return []

# 메인 앱 구성
def main():
    # CSS 스타일 적용
    st.markdown(get_css(), unsafe_allow_html=True)
    
    # 헤더
    render_header()
    
    # 사이드바 설정
    with st.sidebar:
        st.title("⚙️ 설정")
        
        # 초기화 버튼
        if st.button("🧹 모든 데이터 초기화"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            initialize_session_state()
            st.success("모든 데이터가 초기화되었습니다.")
            st.rerun()
        
        st.markdown("---")
        
        # 회사 정보 입력 (사이드바용)
        st.subheader("🏢 내 회사 정보")
        render_company_info_form("sidebar_company_info_form")
        
        st.markdown("---")
        
        # 업데이트 주기 설정
        st.subheader("⏰ 공고 업데이트 주기")
        update_cycle = st.selectbox(
            "업데이트 주기 선택",
            ["수동", "매일", "매주"],
            index=["수동", "매일", "매주"].index(st.session_state.update_cycle)
        )
        if update_cycle != st.session_state.update_cycle:
            st.session_state.update_cycle = update_cycle
            st.success(f"업데이트 주기가 {update_cycle}으로 변경되었습니다.")
    
    # 메인 컨텐츠
    render_dashboard()
    
    # 업데이트 알림
    if check_update_needed():
        st.markdown("""
            <div class="card update-reminder">
                <h4>🔔 공고 업데이트 알림</h4>
                <p>오늘은 공고 수집 예정일입니다. 아래 버튼을 눌러 새 공고를 받아보세요.</p>
            </div>
        """, unsafe_allow_html=True)
    
    # 공고 수집 버튼
    if st.button("🔄 공고 수집하기", type="primary"):
        if not st.session_state.sites:
            st.warning("등록된 사이트가 없습니다. 좌측 사이드바에서 사이트를 먼저 등록해주세요.")
        else:
            with st.spinner("공고를 수집하고 분석하는 중입니다..."):
                try:
                    new_announcements = crawl_and_analyze()
                    if new_announcements:
                        st.session_state.announcements.extend(new_announcements)
                        st.session_state.last_update = datetime.now()
                        st.success(f"{len(new_announcements)}개의 새로운 공고가 수집되었습니다!")
                    else:
                        st.info("새로운 공고를 찾지 못했습니다.")
                except Exception as e:
                    st.error(f"공고 수집 중 오류가 발생했습니다: {str(e)}")
            st.rerun()
    
    # 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 사이트 관리", "🎯 맞춤 추천", "📊 전체 공고", "📝 텍스트 분석", "⚙️ 설정"])
    
    with tab1:
        render_sites_tab()
    
    with tab2:
        render_recommended_tab()
    
    with tab3:
        render_announcements_tab()
    
    with tab4:
        st.markdown("""
            <h3 style="margin-bottom: 2rem;">📝 공고 텍스트 분석</h3>
            <p>여러 공고가 포함된 텍스트를 입력하면 자동으로 분석하여 등록합니다.</p>
        """, unsafe_allow_html=True)
        
        announcement_text = st.text_area(
            "공고 텍스트 입력",
            height=300,
            help="여러 공고가 포함된 텍스트를 입력하세요. 각 공고는 자동으로 구분되어 분석됩니다."
        )
        
        if st.button("텍스트 분석하기", type="primary"):
            if not announcement_text:
                st.warning("분석할 텍스트를 입력해주세요.")
            else:
                with st.spinner("텍스트를 분석하는 중입니다..."):
                    new_announcements = analyze_announcements_text(announcement_text)
                    if new_announcements:
                        st.session_state.announcements.extend(new_announcements)
                        st.success(f"{len(new_announcements)}개의 공고가 분석되어 등록되었습니다!")
                        
                        # 분석 결과 미리보기
                        st.markdown("### 분석 결과 미리보기")
                        for ann in new_announcements:
                            with st.expander(ann['title']):
                                st.write(f"**기관:** {ann['site_name']}")
                                st.write(f"**접수기간:** {ann['period']}")
                                st.write(f"**지원유형:** {ann['category']}")
                                st.write(f"**요약:** {ann['summary']}")
                                st.write(f"**URL:** {ann['url']}")
                    else:
                        st.error("텍스트 분석 중 오류가 발생했습니다.")
    
    with tab5:
        render_company_info_form("settings_company_info_form")

if __name__ == "__main__":
    main() 
