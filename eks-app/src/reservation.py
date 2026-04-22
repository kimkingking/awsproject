import os
import time
import requests
import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.database import dynamodb, reservation_table, seat_table, rd
from boto3.dynamodb.conditions import Key, Attr

# [설정] 환경변수 및 캡차 키
DEBUG_MODE = os.getenv("DEBUG_MODE", "False") == "True"
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "0x4AAAAAACon_-jaaYDj9s5-")

router = APIRouter()

# ==========================================
# [데이터 모델]
# ==========================================
class PreCheckRequest(BaseModel):
    user_id: str
    perf_id: str
    select_date: str
    select_time: str
    turnstile_token: str = "" 

class ReservationRequest(BaseModel):
    user_id: str
    seat_num: str       
    perf_id: str
    perf_title: str
    select_date: str
    select_time: str
    place: str
    price: int
    turnstile_token: str = "" 

# ==========================================
# [보조 함수] 캡차 검증
# ==========================================
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
# 💡 [예약된 좌석 목록 조회] DynamoDB Query
# ==========================================
@router.get("/seats")
def get_reserved_seats(perf_id: str, date: str, time: str):
    try:
        # seat_table에서 해당 공연/시간에 'OCCUPIED'인 좌석 조회
        # (성능을 위해 GSI나 복합 키 설계가 되어 있다고 가정)
        # 여기서는 단순화를 위해 scan에 필터를 사용하지만, 운영에서는 Query 권장
        response = seat_table.scan(
            FilterExpression=Attr('perf_id').eq(perf_id) & 
                             Attr('perf_date').eq(date) & 
                             Attr('perf_time').eq(time) & 
                             Attr('status').eq('OCCUPIED')
        )
        reserved_seats = [item['seat_num'] for item in response.get('Items', [])]
        return {"status": "success", "reserved_seats": reserved_seats}
    except Exception as e:
        return {"status": "error", "message": f"DynamoDB 조회 오류: {str(e)}"}

# ==========================================
# [API 1] 사전 진입 검증 (대기열 체크)
# ==========================================
@router.post("/reserve")
def reserve_precheck(req: PreCheckRequest):
    try:
        is_allowed = rd.sismember("allowed_users", req.user_id)
        if not is_allowed:
            now = time.time()
            rd.zadd("ticket_queue", {req.user_id: now}, nx=True)
            rank = rd.zrank("ticket_queue", req.user_id) + 1
            return {"status": "wait", "message": "아직 예매 순서가 아닙니다.", "waiting_number": rank}
        return {"status": "success", "message": "검증 완료. 좌석 선택으로 이동합니다."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# [API 2] 최종 예매 진행 (DynamoDB Transaction)
# ==========================================
@router.post("/confirm")
def confirm_reservation(req: ReservationRequest):
    try:
        # 1. 캡차 검증
        is_test_mode = (DEBUG_MODE and req.turnstile_token in ["", "JETER_TEST_TOKEN"])
        if not is_test_mode:
            if not verify_turnstile_sync(req.turnstile_token):
                raise HTTPException(status_code=403, detail="캡차 검증 실패")

        # 좌석 고유 키 (예: 공연ID + 날짜 + 시간 + 좌석번호)
        seat_key = f"{req.perf_id}#{req.select_date}#{req.select_time}#{req.seat_num}"
        res_id = f"RES#{int(time.time()*1000)}#{req.user_id}"

        # 2. DynamoDB Transaction 실행 (좌석 선점 + 예약 생성)
        # ConditionExpression을 사용하여 status가 'AVAILABLE'일 때만 업데이트 (동시성 제어)
        try:
            dynamodb.meta.client.transact_write_items(
                TransactItems=[
                    {
                        'Update': {
                            'TableName': 'Seat',
                            'Key': {'seat_id': seat_key},
                            'UpdateExpression': 'SET #stat = :occ',
                            'ConditionExpression': 'attribute_not_exists(seat_id) OR #stat = :avail',
                            'ExpressionAttributeNames': {'#stat': 'status'},
                            'ExpressionAttributeValues': {
                                ':occ': 'OCCUPIED',
                                ':avail': 'AVAILABLE'
                            }
                        }
                    },
                    {
                        'Put': {
                            'TableName': 'Reservation',
                            'Item': {
                                'res_id': res_id,
                                'user_id': req.user_id,
                                'seat_num': req.seat_num,
                                'perf_id': req.perf_id,
                                'perf_title': req.perf_title,
                                'select_date': req.select_date,
                                'select_time': req.select_time,
                                'place': req.place,
                                'price': req.price,
                                'res_date': time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                        }
                    }
                ]
            )
        except dynamodb.meta.client.exceptions.TransactionCanceledException as e:
            # 트랜잭션 실패 원인이 조건 미충족(이미 예약됨)인지 확인
            for reason in e.response['CancellationReasons']:
                if reason['Code'] == 'ConditionalCheckFailed':
                    return {"status": "fail", "message": "이미 예약이 완료된 좌석입니다."}
            raise e

        # 3. 예매 성공 후 대기열 제거
        rd.srem("allowed_users", req.user_id)
        return {"status": "success", "message": "🎉 DynamoDB 예매 성공!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
