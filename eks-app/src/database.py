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

# 2️⃣ DynamoDB 설정 (환경 변수 적용 및 세션 최적화)
# YAML에서 설정한 값을 읽어오고, 없을 경우를 대비해 기본값(Default)을 설정합니다.
REGION = os.getenv("AWS_REGION", "ap-northeast-2")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "ticket")

# EKS IRSA(IAM Role) 환경에서는 Session을 명시적으로 생성하는 것이 자격 증명을 가져오는 데 더 정확합니다.
session = boto3.Session(region_name=REGION)
dynamodb = session.resource('dynamodb')

# 공통으로 사용할 테이블 객체
table = dynamodb.Table("ticket")

# 서버 로그에서 연결 정보를 확인할 수 있도록 출력문을 추가하면 디버깅이 편합니다.
print(f"--- DynamoDB 연결 설정 완료: 리전({REGION}), 테이블({TABLE_NAME}) ---")
