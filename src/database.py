import boto3
import redis
import os

# 1️⃣ Redis 설정 (기존 유지)
rd = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis-service"),
    port=6379,
    db=0,
    decode_responses=True
)

# 2️⃣ DynamoDB 설정 (수정됨)
# 명시적으로 Session을 생성하여 리전을 고정합니다.
# 이렇게 하면 환경 변수가 꼬여도 'ap-northeast-2'를 우선적으로 바라봅니다.
session = boto3.Session(region_name='ap-northeast-2')
dynamodb = session.resource('dynamodb')

# 테이블 객체 정의
table = dynamodb.Table('ticket')

# 🔍 서버 실행 시 연결 정보를 터미널에 출력 (추가된 부분)
# 이 로그가 터미널에 찍혀야 수정된 코드가 '진짜로' 반영된 것입니다.
print("\n" + "="*40)
print(f"🚀 DynamoDB 연결 정보 확인")
print(f"📍 REGION: {session.region_name}")
print(f"📋 TABLE: {table.table_name}")
try:
    # 실제로 테이블에 접근 가능한지 살짝 찔러보기
    _ = table.creation_date_time
    print("✅ STATUS: 연결 성공 (Table exists)")
except Exception as e:
    print(f"❌ STATUS: 연결 실패 ({e})")
print("="*40 + "\n")
