# 🌐 EchoChamber 배포 가이드 (로컬 서버 없이 웹 접속)

로컬 PC에서 서버를 켜두지 않고, 언제 어디서나 웹 브라우저 URL로 접속할 수 있도록 배포하는 가이드입니다.

---

## 📌 배포 방식 선택

| 배포 방식 | 접속 주소 예시 | 특징 및 용도 |
| :--- | :--- | :--- |
| **방법 1: GitHub Pages (정적 웹)** ⭐ | `https://min8309.github.io/echoChamber/` | **서버 유지비 0원, 슬립 없음, 즉각 로딩.** 인터랙티브 시뮬레이션 및 분석 UI 상시 구동 |
| **방법 2: Render (FastAPI 백엔드)** | `https://echochamber.onrender.com` | Python 백엔드 API + OpenAI 모델 실시간 연동 |
| **방법 3: Streamlit Community Cloud** | `https://echochamber.streamlit.app` | `dashboard.py` 데이터 시각화 대시보드 단독 배포 |

---

## 1. 방법 1: GitHub Pages 정적 배포 (https://min8309.github.io/echoChamber/) ⭐

루트에 생성된 `index.html`과 정적 프론트엔드 엔진을 통해 **GitHub Pages에서 서버 없이 즉시 구동**됩니다.

### 🚀 1분 활성화 순서:
1. **GitHub에 최신 코드 푸시**:
   ```bash
   git add .
   git commit -m "feat: GitHub Pages 정적 배포 지원 (index.html 및 상대경로 라우팅)"
   git push origin main
   ```
2. **GitHub 저장소 페이지 접속**:
   - `https://github.com/min8309/echoChamber` (또는 본인 저장소)
3. **Settings (설정) ➜ Pages 메뉴 이동**:
   - 저장소 상단 탭에서 **`Settings`** 클릭
   - 좌측 메뉴에서 **`Pages`** 클릭
4. **Build and deployment 설정**:
   - **Source**: `Deploy from a branch` 선택
   - **Branch**: `main` 선택 / 폴더: `/ (root)` 선택
   - **`Save`** 버튼 클릭
5. **접속 확인**:
   - 약 1~2분 후 GitHub Pages 상단에 녹색 체크와 함께 사이트 주소가 활성화됩니다:
   - 👉 **[https://min8309.github.io/echoChamber/](https://min8309.github.io/echoChamber/)**

---

## 2. 방법 2: Render 무료 웹 서비스 배포 (FastAPI 백엔드 연동)

[Render](https://render.com)는 백엔드 Python 서버(uvicorn)와 OpenAI API 연동이 필요한 경우 무료로 호스팅할 수 있습니다.

### 배포 순서:
1. **[Render](https://render.com) 접속 및 GitHub 계정으로 로그인**.
2. 대시보드 우측 상단 **`New +`** 버튼 클릭 ➜ **`Web Service`** 선택.
3. GitHub 저장소(`echoChamber`) 연결 (**Connect**).
4. 설정값 확인:
   - **Name**: `echochamber`
   - **Region**: `Singapore` (또는 가까운 리전)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
5. **환경 변수(Environment Variables) 설정**:
   - **Environment Variables** ➜ **`Add Environment Variable`**
   - `OPENAI_API_KEY`: 사용자 본인의 OpenAI API 키
   - `OPENAI_MODEL`: `gpt-4o-mini`
6. **`Create Web Service`** 클릭 (약 2~3분 후 URL 발급).

---

## 3. 방법 3: Streamlit Community Cloud (대시보드 전용)

`dashboard.py` (Streamlit 대시보드)를 무료 배포하고 싶을 때 사용합니다.

1. **[share.streamlit.io](https://share.streamlit.io)** 접속 및 로그인.
2. **`Create app`** 클릭.
3. GitHub 저장소(`echoChamber`), 브랜치(`main`), 메인 파일 경로(`dashboard.py`) 지정.
4. **`Advanced settings`** ➜ **Secrets**에 OpenAI API Key 설정:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
5. **`Deploy`** 클릭.

---

## 4. 페이지 구성 및 정적 링크 안내

GitHub Pages(`https://min8309.github.io/echoChamber/`) 접속 시 지원되는 화면:

| 페이지 | 상대 경로 | 설명 |
| :--- | :--- | :--- |
| **메인 대시보드** | `/` (`index.html`) | 가상 마을(Smallville) 시뮬레이션, 메신저 피드, 소문 확산 네트워크 토폴로지 |
| **현실 댓글 연구실** | `stitch/code_01.html` | 실제 댓글 CSV 파싱 및 텍스트 왜곡/신뢰도 분석 연구실 |
| **미디어 리터러시 교육실** | `stitch/code_02.html` | 소문 탐정(Rumor Detective) 미션 및 팩트체크 교육 랩 |
| **알렉산드리아 아카이브** | `stitch/alexandria/code.html` | 소문 전파 단계별 인터랙티브 아카이브 뷰 |
