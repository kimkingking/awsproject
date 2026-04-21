import bcrypt
from fastapi import APIRouter, Form, Response
from src.database import user_table

router = APIRouter(prefix="/api/member")

@router.post("/login")
def login(
    response: Response,
    u_id: str = Form(...),
    u_pass: str = Form(...)
):
    try:
        # 💡 MySQL 쿼리 대신 DynamoDB GetItem 사용 (Partition Key: user_id)
        res = user_table.get_item(Key={'user_id': u_id})
        user = res.get('Item')

        # 1. 유저 존재 확인
        if user:
            db_password = user.get('password')
            user_name = user.get('user_name')
            email = user.get('email')
            
            # 2. bcrypt 비밀번호 검증 (평문 vs 해시값)
            if db_password and bcrypt.checkpw(u_pass.encode('utf-8'), db_password.encode('utf-8')):
                return {
                    "status": "success",
                    "message": f"{user_name}님, 환영합니다!",
                    "nickname": user_name,
                    "email": email
                }
            else:
                return {
                    "status": "fail",
                    "message": "아이디 또는 비밀번호가 일치하지 않습니다."
                }
        else:
            return {
                "status": "fail",
                "message": "아이디 또는 비밀번호가 일치하지 않습니다."
            }

    except Exception as e:
        return {"status": "error", "message": f"로그인 중 오류 발생: {str(e)}"}
