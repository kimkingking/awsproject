import boto3
import redis
import os

# AWS 리전 설정 (환경 변수에서 가져오거나 기본값 'ap-northeast-2' 사용)
region_name = os.getenv("AWS_REGION", "ap-northeast-2")

# DynamoDB 리소스 초기화
# EKS에서는 IAM Role(IRSA)을 통해 별도의 AccessKey 없이 접근하도록 설정하는 것이 보안상 좋음.
dynamodb = boto3.resource('dynamodb', region_name=region_name)

# 테이블 객체 (사용 시 호출)
reservation_table = dynamodb.Table('Reservation')
user_table = dynamodb.Table('User')
seat_table = dynamodb.Table('Seat')

# Redis 설정은 유지 (대기열 관리용)
rd = redis.Redis(host='redis-service.ticketing.svc.cluster.local', port=6379, db=0, decode_responses=True)