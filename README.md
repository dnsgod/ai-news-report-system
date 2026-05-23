# AI News Report System

네이버 뉴스 헤드라인을 크롤링하고,
로컬 LLM(Ollama)을 활용해 뉴스 요약 및 키워드 분석 리포트를 생성하는 프로젝트입니다.

## 기능

- 뉴스 헤드라인 크롤링
- 기사 본문 수집
- 로컬 LLM 뉴스 요약
- 섹션별 핵심 흐름 요약
- 키워드 추출
- 유사 기사 제거
- 최근 반복 키워드 분석
- 급상승 키워드 탐지

## 사용 기술

- Python
- BeautifulSoup
- Requests
- Ollama (Qwen2.5)

## 실행 방법

```bash
python crawler.py
python report_generator.py