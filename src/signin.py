import re
import bcrypt
from fastapi import APIRouter, Form
from botocore.exceptions import ClientError
from database import table

router = APIRouter(prefix="/api/member")

def format_phone_number(phone: str) -> str:
    clean_number = re.sub(r'[^0-9]', '', phone)
    if len(clean_number) == 11:
        return f"{clean_number[:3]}-{clean_number[3:7]}-{clean_number[7:]}"
    elif len(clean_number) == 10:
        return f"{clean_number[:3]}-{clean_number[3:6]}-{clean_number[6:]}"
    return phone

@router.post("/register")
def register(
    user_id: str = Form(...),
    password: str = Form(...),
    user_name: str = Form(...),
    phone: str = Form(...),
    addr: str = Form(...),
    email: str = Form(...)
):
    try:
        # 로그추가
        print("REGISTER INPUT:", user_id, password, user_name, phone, addr, email)
        formatted_phone = format_phone_number(phone)

        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        table.put_item(
            Item={
                "PK": f"USER#{user_id}",
                "SK": "METADATA",
                "user_id": user_id,
                "password": hashed_password,
                "user_name": user_name,
                "phone": formatted_phone,
                "addr": addr,
                "email": email,
                "type": "USER"
            },
            ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)"
        )

        return {"status": "success", "message": "가입되었습니다"}

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {"status": "fail", "message": "이미 존재하는 아이디입니다."}

        print(f"DynamoDB Error: {e}")
        return {"status": "fail", "message": "가입 실패"}
