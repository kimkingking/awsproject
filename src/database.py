import boto3
import redis
import os

# 1️⃣ Redis 설정 (기존 유지)
# 호스트명은 K8S 서비스 이름인 'redis-service'를 그대로 사용합니다.
rd = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis-service"), 
    port=6379, 
    db=0, 
    decode_responses=True
)

# 2️⃣ DynamoDB 설정 (새로 추가)
# AWS 환경(EKS/Lambda)에서는 IAM Role을 사용하므로 별도의 액세스 키 입력 없이 리소스만 정의합니다.
dynamodb = boto3.resource(
    'dynamodb', 
    region_name='ap-northeast-2'
)

# 공통으로 사용할 테이블 객체 (테이블명이 'ticket'인 경우)
table = dynamodb.Table('ticket')
