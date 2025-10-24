from fastapi import FastAPI, HTTPException, Query  
from pydantic import BaseModel
import os
import requests
import json
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional

# 환경변수 로드
load_dotenv()

app = FastAPI(
    title="Restaurant Search API",
    description="OpenAI와 Kakao Map API를 연동한 맛집 검색 서비스",
    version="1.0.0"
)

# API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

# OpenAI 클라이언트는 실제 사용할 때 초기화
openai_client = None

def get_openai_client():
    """OpenAI 클라이언트를 지연 초기화"""
    global openai_client
    if openai_client is None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        try:
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            raise ValueError(f"OpenAI 클라이언트 초기화 실패: {e}")
    return openai_client

class SearchResponse(BaseModel):
    """검색 응답 모델"""
    extracted_keywords: dict
    kakao_results: dict

def extract_keywords_with_openai(query: str) -> dict:
    """
    OpenAI API를 사용하여 쿼리에서 식당 종류, 분위기, 지역 키워드를 추출합니다.
    """
    try:
        prompt = f"""
다음 문장에서 음식점/음주점 검색에 필요한 키워드를 정확히 추출해주세요.

추출할 정보:
1. 음식/업장 종류: 
   - 구체적인 음식명이 있으면 그대로 사용: 삼겹살, 치킨, 피자, 파스타, 짜장면, 냉면, 김치찌개 등
   - 업장 종류: 한식, 중식, 일식, 양식, 분식, 카페, 바, 술집, 펍, 디저트 등
   
2. 분위기: 조용한, 활기찬, 로맨틱한, 캐주얼한, 고급스러운, 아늑한, 모던한 등

3. 지역: 시/구/동 단위의 지역명 (예: 인계동, 수원, 강남, 홍대, 명동 등)

문장: "{query}"

중요 규칙:
- 구체적인 음식명(삼겹살, 치킨, 피자 등)이 나오면 절대 일반화하지 말고 그대로 사용하세요
- 예: "삼겹살" → "삼겹살" (한식으로 바꾸지 말 것)
- 예: "치킨" → "치킨" (양식으로 바꾸지 말 것)

JSON 형식으로만 응답:
{{
    "food_type": "구체적인 음식명 또는 업장 종류 또는 null",
    "atmosphere": "분위기 또는 null", 
    "location": "지역 또는 null"
}}
"""
        
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 음식점 검색 키워드 추출 전문가입니다. 구체적인 음식명이 언급되면 절대 일반화하지 말고 그대로 추출하세요. JSON 형식으로만 응답하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        keywords_text = response.choices[0].message.content.strip()
        
        # JSON 파싱
        try:
            keywords = json.loads(keywords_text)
            return keywords
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 기본값 반환
            return {"food_type": None, "atmosphere": None, "location": None}
            
    except Exception as e:
        print(f"OpenAI API 오류: {e}")
        return {"food_type": None, "atmosphere": None, "location": None}

def search_kakao_places(keywords: dict, original_query: str) -> dict:
    """
    Kakao Map API를 사용하여 장소를 검색합니다.
    """
    try:
        # 검색 쿼리 구성
        search_query = ""
        if keywords.get("location"):
            search_query += keywords["location"] + " "
        if keywords.get("food_type"):
            search_query += keywords["food_type"] + " "
        
        # food_type이 없을 때만 "맛집" 추가
        if not keywords.get("food_type"):
            search_query += "맛집"
        
        # 검색어가 없으면 원본 쿼리 사용
        if not search_query.strip():
            search_query = original_query
        
        # Kakao API 키 확인
        if not KAKAO_API_KEY:
            raise ValueError("KAKAO_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        
        # 카테고리 코드 결정
        category_code = "FD6"  # 기본: 음식점
        if keywords.get("food_type"):
            food_type = keywords["food_type"].lower()
            if any(keyword in food_type for keyword in ["카페", "커피", "디저트"]):
                category_code = "CE7"  # 카페
        
        # Kakao Local API 호출
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {
            "Authorization": f"KakaoAK {KAKAO_API_KEY}"
        }
        params = {
            "query": search_query.strip(),
            "category_group_code": category_code,
            "size": 15,  # 최대 15개 결과
            "sort": "accuracy"  # 정확도순 정렬
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Kakao API 오류: {e}")
        return {"documents": [], "meta": {"total_count": 0}}
    except Exception as e:
        print(f"장소 검색 오류: {e}")
        return {"documents": [], "meta": {"total_count": 0}}

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Restaurant Search API", 
        "version": "1.0.0",
        "endpoints": {
            "/search": "맛집 검색 (query 파라미터 필요)",
            "/docs": "API 문서"
        }
    }

@app.get("/search", response_model=SearchResponse)
async def search_restaurants(
    query: str = Query(..., description="검색할 문장 (예: '강남에서 조용한 한식집 찾아줘')")
):
    """
    문장을 입력받아 OpenAI로 키워드를 추출하고, Kakao Map API로 맛집을 검색합니다.
    
    - **query**: 검색할 문장 (식당 종류, 분위기, 지역 등이 포함된 자연어)
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="검색 쿼리가 비어있습니다.")
    
    try:
        # 1. OpenAI API로 키워드 추출
        extracted_keywords = extract_keywords_with_openai(query)
        
        # 2. Kakao Map API로 장소 검색  
        kakao_results = search_kakao_places(extracted_keywords, query)
        
        # 3. 결과 반환
        return SearchResponse(
            extracted_keywords=extracted_keywords,
            kakao_results=kakao_results
        )
        
    except Exception as e:
        print(f"검색 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(e)}")

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "message": "API 서버가 정상적으로 동작중입니다."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)