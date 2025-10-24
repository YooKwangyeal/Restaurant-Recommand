# 🍽️ Restaurant Search API

OpenAI GPT와 Kakao Map API를 연동한 맛집 검색 백엔드 서버입니다.

자연어 문장을 입력받아 음식 종류, 분위기, 지역을 추출하고 실제 맛집 정보를 제공합니다.

## 🚀 주요 기능

- **자연어 처리**: OpenAI GPT를 사용하여 검색 문장에서 키워드 추출
- **실시간 검색**: Kakao Map API를 통한 실제 맛집 정보 제공
- **RESTful API**: FastAPI 기반의 간단하고 빠른 API 서버
- **자동 문서화**: `/docs` 엔드포인트에서 Swagger UI 제공

## 📋 요구사항

- Python 3.8+
- OpenAI API Key
- Kakao Developers REST API Key

## 🛠️ 설치 및 설정

### 1. 프로젝트 클론/다운로드

```bash
cd fastapi-kakao-openai
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env` 파일을 수정하여 API 키를 입력하세요:

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Kakao API Key (REST API Key)
KAKAO_API_KEY=your_kakao_api_key_here
```

#### API 키 발급 방법:

**OpenAI API Key:**

1. [OpenAI Platform](https://platform.openai.com/) 접속
2. 계정 생성/로그인 후 API Keys 메뉴에서 키 생성

**Kakao API Key:**

1. [Kakao Developers](https://developers.kakao.com/) 접속
2. 내 애플리케이션 > 앱 생성 > REST API 키 확인

## 🚀 실행 방법

### 방법 1: 배치 파일 사용 (Windows)

```bash
run_server.bat
```

### 방법 2: 직접 실행

```bash
python main.py
```

### 방법 3: uvicorn 사용

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면 다음 주소에서 확인할 수 있습니다:

- **서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📚 API 사용법

### `/search` 엔드포인트

**GET** `/search?query={검색문장}`

#### 요청 예시:

```bash
# curl 사용
curl "http://localhost:8000/search?query=강남에서 조용한 한식집 찾아줘"

# 브라우저
http://localhost:8000/search?query=홍대 맛있는 피자집 추천해줘
```

#### 응답 예시:

```json
{
  "extracted_keywords": {
    "food_type": "한식",
    "atmosphere": "조용한",
    "location": "강남"
  },
  "kakao_results": {
    "documents": [
      {
        "place_name": "맛있는 한식당",
        "address_name": "서울 강남구 역삼동 123-45",
        "phone": "02-1234-5678",
        "place_url": "http://place.map.kakao.com/12345",
        "category_name": "음식점 > 한식 > 백반, 가정식",
        "x": "127.1234567",
        "y": "37.1234567"
      }
    ],
    "meta": {
      "total_count": 15
    }
  }
}
```

### 기타 엔드포인트

- **GET** `/`: 서버 정보 및 사용 가능한 엔드포인트 목록
- **GET** `/health`: 서버 상태 확인

## 🏗️ 프로젝트 구조

```
fastapi/
├── main.py              # 메인 FastAPI 애플리케이션
├── requirements.txt     # Python 패키지 종속성
├── .env                 # 환경변수 (실제 API 키)
├── .env.example         # 환경변수 예시 파일
├── run_server.bat       # Windows 실행 스크립트
└── README.md           # 프로젝트 문서
```

## 🔧 주요 라이브러리

- **FastAPI**: 현대적이고 빠른 Python 웹 프레임워크
- **OpenAI**: GPT 모델을 사용한 자연어 처리
- **Requests**: HTTP 요청을 위한 라이브러리
- **Python-dotenv**: 환경변수 관리
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증 및 직렬화

## 🚨 주의사항

1. **API 키 보안**: `.env` 파일은 절대 공개 저장소에 업로드하지 마세요
2. **사용량 관리**: OpenAI API는 토큰 기반 과금이므로 사용량을 모니터링하세요
3. **Rate Limiting**: Kakao API는 일일 호출 제한이 있습니다

## 🛠️ 커스터마이징

### OpenAI 모델 변경

`main.py`의 `extract_keywords_with_openai` 함수에서 모델을 변경할 수 있습니다:

```python
model="gpt-4"  # 더 정확한 결과를 원한다면
```

### 검색 결과 개수 조정

`search_kakao_places` 함수의 `size` 파라미터를 수정하세요:

```python
"size": 30,  # 최대 30개 결과
```

## 📞 문의사항

프로젝트 관련 문의사항이 있으시면 이슈를 등록해 주세요.

---

**Made with ❤️ using FastAPI, OpenAI, and Kakao Map API**
