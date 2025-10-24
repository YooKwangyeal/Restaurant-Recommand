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
    raw_places: dict
    filtered_recommendations: list

def extract_keywords_with_openai(query: str) -> dict:
    """
    OpenAI API를 사용하여 쿼리에서 식당 종류, 분위기, 지역 키워드를 추출합니다.
    """
    try:
        prompt = f"""
다음 문장을 음식점/음주점 검색에 필요한 3가지 키워드로 정확히 분석해주세요.

문장: "{query}"

추출할 정보:
1. region (지역): 시/구/동 단위의 지역명
   - 예: 수원, 인계동, 강남구, 홍대, 명동, 서울역 등

2. category (카테고리): 구체적인 음식명이나 업장 종류
   - 구체적인 음식: 삼겹살, 치킨, 피자, 파스타, 짜장면, 냉면, 김치찌개 등
   - 업장 종류: 한식, 중식, 바, 카페, 술집, 펍, 디저트 등

3. mood (감성/분위기): 원하는 분위기나 특성
   - 예: 분위기 좋은, 조용한, 활기찬, 로맨틱한, 고급스러운, 아늑한, 데이트하기 좋은 등

중요 규칙:
- 구체적인 음식명이 나오면 절대 일반화하지 말고 그대로 사용
- mood는 감성적 표현이나 분위기 관련 표현만 추출
- 없는 정보는 null로 처리

JSON 형식으로만 응답:
{{
    "region": "지역명 또는 null",
    "category": "구체적인 음식명/업장종류 또는 null",
    "mood": "감성/분위기 키워드 또는 null"
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
            return {"region": None, "category": None, "mood": None}
            
    except Exception as e:
        print(f"OpenAI API 오류: {e}")
        return {"region": None, "category": None, "mood": None}

def search_kakao_places(keywords: dict, original_query: str) -> dict:
    """
    Kakao Map API를 사용하여 기본 장소 리스트를 검색합니다.
    region + category 조합으로 검색하고, mood는 후처리에서 사용합니다.
    """
    try:
        # 검색 쿼리 구성 (region + category만 사용)
        search_query = ""
        if keywords.get("region"):
            search_query += keywords["region"] + " "
        if keywords.get("category"):
            search_query += keywords["category"] + " "
        
        # category가 없을 때만 "맛집" 추가
        if not keywords.get("category"):
            search_query += "맛집"
        
        # 검색어가 없으면 원본 쿼리 사용
        if not search_query.strip():
            search_query = original_query
        
        # Kakao API 키 확인
        if not KAKAO_API_KEY:
            raise ValueError("KAKAO_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        
        # 카테고리 코드 결정
        category_code = "FD6"  # 기본: 음식점
        if keywords.get("category"):
            category = keywords["category"].lower()
            if any(keyword in category for keyword in ["카페", "커피", "디저트"]):
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

def filter_places_with_ai(places: list, mood: str) -> list:
    """
    AI를 사용하여 mood 키워드에 맞는 장소들을 필터링하고 점수를 매깁니다.
    """
    if not mood or not places:
        # mood가 없거나 장소가 없으면 원래 리스트 그대로 반환
        return [{"place": place, "score": 5, "reason": "기본 검색 결과"} for place in places]
    
    try:
        client = get_openai_client()
        
        # 장소 정보를 간단하게 정리
        places_info = []
        for place in places[:10]:  # 최대 10개만 분석 (API 비용 고려)
            place_summary = {
                "name": place.get("place_name", ""),
                "category": place.get("category_name", ""),
                "address": place.get("address_name", "")
            }
            places_info.append(place_summary)
        
        prompt = f"""
다음 장소들 중에서 "{mood}" 조건에 얼마나 잘 맞는지 각각 1-10점으로 평가하고 이유를 설명해주세요.

원하는 조건: {mood}

장소 목록:
{json.dumps(places_info, ensure_ascii=False, indent=2)}

각 장소에 대해 다음과 같이 평가해주세요:
- 점수: 1-10점 (10점이 가장 좋음)
- 이유: 왜 이 점수를 줬는지 간단한 설명

JSON 형식으로 응답:
[
    {{"index": 0, "score": 8, "reason": "카테고리나 위치가 조건에 잘 맞는 이유"}},
    {{"index": 1, "score": 6, "reason": "평가 이유"}},
    ...
]
"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 음식점 추천 전문가입니다. 장소 정보를 보고 사용자의 조건에 얼마나 잘 맞는지 객관적으로 평가하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        try:
            evaluations = json.loads(ai_response)
            
            # 평가 결과를 바탕으로 장소들을 정렬하고 점수 추가
            filtered_places = []
            for eval_item in evaluations:
                if eval_item["index"] < len(places):
                    place = places[eval_item["index"]]
                    filtered_places.append({
                        "place": place,
                        "score": eval_item["score"],
                        "reason": eval_item["reason"]
                    })
            
            # 점수순으로 정렬 (높은 점수부터)
            filtered_places.sort(key=lambda x: x["score"], reverse=True)
            return filtered_places
            
        except json.JSONDecodeError:
            print(f"AI 응답 파싱 실패: {ai_response}")
            return [{"place": place, "score": 5, "reason": "AI 분석 실패"} for place in places]
            
    except Exception as e:
        print(f"AI 필터링 오류: {e}")
        return [{"place": place, "score": 5, "reason": "AI 분석 오류"} for place in places]

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
    query: str = Query(..., description="검색할 문장 (예: '수원 분위기 좋은 바 추천해줘')")
):
    """
    새로운 3단계 추천 시스템:
    1. AI로 region, category, mood 키워드 추출
    2. region + category로 기본 장소 검색 
    3. AI가 mood 기반으로 장소들을 평가하고 필터링
    
    - **query**: 검색할 문장 (지역, 카테고리, 감성 키워드 포함 자연어)
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="검색 쿼리가 비어있습니다.")
    
    try:
        # 1단계: AI로 키워드 추출 (region, category, mood)
        extracted_keywords = extract_keywords_with_openai(query)
        
        # 2단계: region + category로 기본 장소 리스트 검색
        raw_places = search_kakao_places(extracted_keywords, query)
        
        # 3단계: AI가 mood 기반으로 장소들을 평가하고 필터링
        places_list = raw_places.get("documents", [])
        mood = extracted_keywords.get("mood")
        filtered_recommendations = filter_places_with_ai(places_list, mood)
        
        # 결과 반환
        return SearchResponse(
            extracted_keywords=extracted_keywords,
            raw_places=raw_places,
            filtered_recommendations=filtered_recommendations
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