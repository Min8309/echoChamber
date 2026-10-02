# 베이스 이미지: 경량화된 Python 3.11 Slim
FROM python:3.11-slim

# 표준 출력 버퍼링 비활성화 및 바이트코드 생성 방지
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8008

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (필요시 빌드 도구)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 패키지 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 코드 및 데이터 복사
COPY . .

# 데이터 디렉토리 권한 확보
RUN mkdir -p data

# 포트 노출
EXPOSE 8008

# 서버 실행 (클라우드 환경의 $PORT 환경변수 지원)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8008}"]
