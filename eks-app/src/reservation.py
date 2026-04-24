import os
import time
import json
import boto3
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.database import rd, table
from boto3.dynamodb.conditions import Key

# [설정] 환경변수 및 AWS 설정
DEBUG_MODE = os.getenv("DEBUG_MODE", "False") == "True"
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
SQS_QUEUE_URL = "https://sqs.ap-northeast-2.amazonaws.com/857281493476/ticket-booking-SQS.fifo"

if not TURNSTILE_SECRET_KEY:
    raise RuntimeError("TURNSTILE_SECRET_KEY is not set. Server cannot start.")

# AWS 클라이언트 및 리소스 초기화
sqs = boto3.client('sqs', region_name='ap-northeast-2')

router = APIRouter()

# [데이터 모델] 동일하게 유지
class PreCheckRequest(BaseModel):
    u_id: str
    perf_id: str
    select_date: str
    select_time: str
    turnstile_token: str = "" 

class ReservationRequest(BaseModel):
    u_id: str
    seat_num: str       
    perf_id: str
    perf_title: str
    select_date: str
    select_time: str
    place: str
    price: int
    turnstile_token: str = "" 

# [보조 함수] 캡차 검증 동일
def verify_turnstile_sync(token: str) -> bool:
    if not TURNSTILE_SECRET_KEY or not token: return False
    try:
        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": TURNSTILE_SECRET_KEY, "response": token},
            timeout=5.0
        )
        return response.json().get("success", False)
    except Exception as e:
        return False

# ==========================================
# 💡 [수정] 예약된 좌석 목록 조회 (DynamoDB 버전)
# ==========================================
@router.get("/seats")
def get_reserved_seats(perf_id: str):
    try:
        # DynamoDB에서 해당 공연의 모든 좌석 정보를 가져옵니다.
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"PERF#{perf_id}") & 
                                   Key("SK").begins_with("SEAT#")
        )
        
        items = response.get("Items", [])
        
        # 'status'가 'OCCUPIED'인 데이터만 골라서 좌석 번호(SK의 뒷부분) 리스트 생성
        reserved_seats = [
            item['SK'].replace("SEAT#", "") 
            for item in items 
            if item.get('status') == 'OCCUPIED'
        ]
        
        return {"status": "success", "reserved_seats": reserved_seats}
    except Exception as e:
        return {"status": "error", "message": f"좌석 조회 실패: {str(e)}"}

# ==========================================
# [API 1] 사전 진입 검증 (대기열 로직)
# ==========================================
@router.post("/reserve")
def reserve_precheck(req: PreCheckRequest):
    try:
        is_allowed = rd.sismember("allowed_users", req.u_id)
        if not is_allowed:
            now = time.time()
            rd.zadd("ticket_queue", {req.u_id: now}, nx=True)
            rank = rd.zrank("ticket_queue", req.u_id) + 1
            return {"status": "wait", "message": "아직 예매 순서가 아닙니다.", "waiting_number": rank}

        return {"status": "success", "message": "검증 완료. 좌석 선택으로 이동합니다."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# [API 2] 최종 예매 진행 (SQS 전송)
# ==========================================
@router.post("/confirm")
def confirm_reservation(req: ReservationRequest):
    try:
        # 1. 캡차 검증
        is_test_mode = (DEBUG_MODE and req.turnstile_token in ["", "JETER_TEST_TOKEN"])
        if not is_test_mode:
            if not verify_turnstile_sync(req.turnstile_token):
                raise HTTPException(status_code=403, detail="캡차 검증 실패")

        # 2. SQS 메시지 전송
        message_body = req.dict()
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body, ensure_ascii=False),
            MessageGroupId=f"{req.perf_id}_{req.seat_num}",
            MessageDeduplicationId=f"{req.u_id}_{req.perf_id}_{req.seat_num}"
        )

        # 3. Redis 권한 제거
        rd.srem("allowed_users", req.u_id)

        return {
            "status": "success", 
            "message": "🎉 예매 요청이 접수되었습니다! 잠시 후 내 예약 목록을 확인해주세요."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
