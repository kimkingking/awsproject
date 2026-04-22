import bcrypt
from fastapi import APIRouter, Form, Response
from database import table  # 👈 핵심 (여기만 쓰면 됨)

router = APIRouter(prefix="/api/member")

@router.post("/login")
def login(
    response: Response,
    u_id: str = Form(...),
    u_pass: str = Form(...)
):

    try:
        # DynamoDB 조회
        res = table.get_item(
            Key={
                "PK": f"USER#{u_id}",
                "SK": "METADATA"
            }
        )

        user_data = res.get("Item")

        if user_data:
            db_password = user_data.get("password", "")
            user_name = user_data.get("user_name")
            email = user_data.get("email")

            if db_password and bcrypt.checkpw(
                u_pass.encode("utf-8"),
                db_password.encode("utf-8")
            ):
            
                return {
                    "status": "success",
                    "message": f"{user_name}님, 환영합니다!",
                    "nickname": user_name,
                    "email": email
                }

        return {
            "status": "fail",
            "message": "아이디 또는 비밀번호가 일치하지 않습니다."
        }

    except Exception as e:
        print(f"Login Error: {str(e)}")
        return {"status": "error", "message": "서버 에러가 발생했습니다."}
