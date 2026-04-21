import re
import bcrypt
from fastapi import APIRouter, Form
from src.database import user_table

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
        formatted_phone = format_phone_number(phone)
        
        # 1. 비밀번호 해싱 (bcrypt)
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # 2. DynamoDB put_item (ConditionExpression을 사용하여 중복 체크)
        try:
            user_table.put_item(
                Item={
                    'user_id': user_id,
                    'password': hashed_password,
                    'user_name': user_name,
                    'phone': formatted_phone,
                    'addr': addr,
                    'email': email
                },
                ConditionExpression='attribute_not_exists(user_id)' # 아이디가 존재하지 않을 때만 성공
            )
            return {"status": "success", "message": "성공적으로 가입되었습니다!"}
        except user_table.meta.client.exceptions.ConditionalCheckFailedException:
            return {"status": "fail", "message": "이미 존재하는 아이디입니다."}

    except Exception as e:
        return {"status": "fail", "message": f"가입 중 오류 발생: {str(e)}"}
