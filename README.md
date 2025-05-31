# 지원사업 적합도 검사 사이트

정부 지원사업 공고를 수집하고 분석하여 기업에 맞는 지원사업을 추천해주는 웹 애플리케이션입니다.

## 주요 기능

- 지원사업 공고 자동 수집
- 텍스트 분석을 통한 지원사업 분류
- 기업 정보 기반 맞춤형 추천
- PDF/Excel 형식 보고서 생성

## 기술 스택

- Python 3.10+
- Streamlit
- Google Gemini API
- BeautifulSoup4
- Pandas

## 설치 및 실행

1. 저장소 클론
```bash
git clone https://github.com/seldystudy/gemini_chatbot2.git
cd gemini_chatbot2
```

2. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

3. Gemini API 키 설정
`.streamlit/secrets.toml` 파일에 API 키를 설정하세요:
```toml
GEMINI_API_KEY="실제_API_키_값"
```

4. 앱 실행
```bash
streamlit run app.py
```

## 배포

이 앱은 Streamlit Cloud를 통해 배포됩니다. 
