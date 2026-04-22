from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import time
import os

# [설정] DB(DynamoDB)와 Redis 연결은 database.py에서 통합 관리합니다.
from src.database import dynamodb, reservation_table, user_table, seat_table, rd
from boto3.dynamodb.conditions import Key

# [보안] 이중 방어용 커스텀 보안 미들웨어
from src.security import SecurityFilterMiddleware

# [라우터]
from src import login, signin, reservation 


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================================
# [미들웨어 등록] 순서가 매우 중요합니다!
# ==========================================

# 1️⃣ 안쪽 껍질: 보안 WAF 미들웨어 (실제 비즈니스 로직 직전에 실행)
app.add_middleware(SecurityFilterMiddleware)

# 2️⃣ 바깥쪽 껍질: CORS 미들웨어 (FastAPI는 나중에 추가한 게 먼저 실행됨)
origins = [
    "https://www.plusticket.store",
    "https://plusticket.store",
    "http://www.plusticket.store",
    "http://plusticket.store",
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
app.include_router(signin.router)
app.include_router(reservation.router, prefix="/api/reservations")

# ==========================================
# [API 엔드포인트]
# ==========================================

@app.get("/")
async def root():
    return {"message": "Welcome to the Integrated Ticketing System (DynamoDB)! 🚀"}

@app.get("/db-test")
def db_test():
    try:
        # 간단한 테이블 조회를 통해 DynamoDB 연결 확인
        reservation_table.scan(Limit=1)
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

# ✨ 예약 내역 조회 API (DynamoDB)
@app.get("/api/reservations/{user_id}")
def get_user_reservations(user_id: str):
    try:
        # user_id가 파티션 키이거나 GSI로 설정되어 있어야 합니다.
        response = reservation_table.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        return response.get('Items', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB 조회 중 오류 발생: {str(e)}")

# ✨ 빈 좌석 조회 API (DynamoDB)
@app.get("/seats")
def get_seats():
    try:
        # 'status'가 'AVAILABLE'인 좌석 조회
        response = seat_table.scan(
            FilterExpression="status = :status",
            ExpressionAttributeValues={":status": "AVAILABLE"}
        )
        return {"available_seats": response.get('Items', [])}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ✨ 단일 유저 조회 API (DynamoDB)
@app.get("/users/{user_id}")
def get_user(user_id: str):
    try:
        response = user_table.get_item(Key={'user_id': user_id})
        item = response.get('Item')
        if item:
            return item
        return {"error": "User not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
