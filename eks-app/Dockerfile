# ECR 테스트
# ECR 테스트 10:17분 PUSH!

FROM public.ecr.aws/docker/library/python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]