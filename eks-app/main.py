from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import time
import os
import boto3
from boto3.dynamodb.conditions import Key

# [설정] 기존 database.py에서 정의한 리소스들을 가져옵니다.
from src.database import table, rd 

# [보안] 이중 방어용 커스텀 보안 미들웨어 (절대 누락 금지!)
from src.security import SecurityFilterMiddleware

# [라우터]
# 파일명이 signing.py인지 signin.py인지 확인 후 맞춰주세요!
from src import login, signin, reservation 

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================================
# [미들웨어 등록] 순서가 매우 중요합니다!
# ==========================================

# 1️⃣ 안쪽 껍질: 보안 WAF 미들웨어
app.add_middleware(SecurityFilterMiddleware)

# 2️⃣ 바깥쪽 껍질: CORS 미들웨어 (기존 도메인 모두 포함)
origins = [
    "https://www.plusticket.store",
    "https://plusticket.store",
    "http://www.plusticket.store",
    "http://plusticket.store",
    "https://www.pulseticket.ke",
    "https://pulseticket.ke",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# [라우터 등록]
# ==========================================
app.include_router(login.router)
app.include_router(signing.router) # 회원가입
app.include_router(reservation.router, prefix="/api/reservations")

# ==========================================
# [API 엔드포인트] - DynamoDB 기반으로 수정됨
# ==========================================

@app.get("/")
async def root():
    return {"message": "Welcome to the Integrated Ticketing System (DynamoDB)! 🚀"}

@app.get("/db-test")
def db_test():
    try:
        # DynamoDB 연결 확인용
        table.load()
        return {"status": "success", "message": "Connected to AWS DynamoDB!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ✨ 대기열 관리자 API (기존 Redis 로직 유지)
@app.post("/next")
def allow_next_users(count: int = 10):
    try:
        top_users = rd.zrange("ticket_queue", 0, count - 1)
        if not top_users:
            return {"status": "success", "message": "현재 대기열이 텅 비어있습니다."}

        rd.sadd("allowed_users", *top_users)
        rd.zrem("ticket_queue", *top_users)

        return {
            "status": "success",
            "message": f"{len(top_users)}명의 유저가 입장 허가를 받았습니다!",
            "allowed_users": top_users
        }
    except Exception as e:
        return {"status": "error", "message": f"대기열 이동 중 오류 발생: {str(e)}"}

# ✨ 예약 내역 조회 API (PK/SK 구조 적용)
@app.get("/api/reservations/{user_id}")
def get_user_reservations(user_id: str):
    try:
        # PK: USER#아이디, SK: RES#로 시작하는 예약내역 쿼리
        response = table.query(
            KeyConditionExpression=Key('PK').eq(f"USER#{user_id}") & 
                                   Key('SK').begins_with("RES#")
        )
        return response.get('Items', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB 조회 중 오류 발생: {str(e)}")

# ✨ 빈 좌석 조회 API (PK/SK 구조 적용)
@app.get("/seats/{perf_id}")
def get_seats(perf_id: str):
    try:
        # 해당 공연(PERF#)의 모든 좌석(SEAT#) 조회
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"PERF#{perf_id}") & 
                                   Key("SK").begins_with("SEAT#")
        )
        all_seats = response.get("Items", [])
        # 'AVAILABLE' 상태인 좌석만 필터링
        available_seats = [s for s in all_seats if s.get("status") == "AVAILABLE"]
        return {"available_seats": available_seats}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ✨ 단일 유저 조회 API (PK/SK 구조 적용)
@app.get("/users/{user_id}")
def get_user(user_id: str):
    try:
        # 유저 메타데이터 직접 조회
        response = table.get_item(
            Key={'PK': f"USER#{user_id}", 'SK': "METADATA"}
        )
        item = response.get('Item')
        if item:
            return item
        return {"error": "User not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
