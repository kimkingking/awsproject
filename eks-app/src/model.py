"""
[DynamoDB Schema Definition]
이 프로젝트는 더 이상 SQLAlchemy(MySQL)를 사용하지 않고 DynamoDB를 사용합니다.
아래는 DynamoDB 테이블의 논리적 구조입니다.

1. Table: Reservation
   - Partition Key (Hash): res_id (String, e.g., "RES#timestamp#userid")
   - Sort Key (Range): user_id (String)
   - Attributes: seat_num, perf_id, perf_title, select_date, select_time, place, price, res_date

2. Table: User
   - Partition Key (Hash): user_id (String)
   - Attributes: password, user_name, phone, addr, email

3. Table: Seat
   - Partition Key (Hash): seat_id (String, e.g., "perfId#date#time#seatNum")
   - Attributes: status ('AVAILABLE', 'OCCUPIED'), seat_num, perf_id, perf_date, perf_time
"""
# 💡 DynamoDB는 스키마리스(Schemaless)이므로 별도의 Class 정의 없이 
#    boto3를 통해 바로 딕셔너리 형태로 데이터를 읽고 씁니다.
