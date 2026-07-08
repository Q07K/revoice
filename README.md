# Revoice

학습 기반 RVC 파이프라인으로 AI 커버곡을 만드는 웹 서비스.

**보컬 분리(RoFormer) → 음성 변환(RVC/Applio) → 믹싱(ffmpeg)**

## 구성

| 디렉터리 | 스택 | 설명 |
|---|---|---|
| [`backend/`](backend/README.md) | FastAPI + SQLAlchemy | Feature-Driven 구조 (voices / trainings / covers), 엔진 추상화 |
| `frontend/` | React + Vite + shadcn/ui | 웜 스튜디오 테마, TanStack Query, 라이트/다크 지원 |

## 실행

```bash
# 백엔드 (http://localhost:8000, API 문서: /docs)
cd backend
uv sync
uv run uvicorn app.main:app --reload

# 프론트엔드 (http://localhost:5173, /api는 백엔드로 프록시)
cd frontend
npm install
npm run dev
```

기본은 GPU 없이 전체 플로우가 동작하는 **mock 엔진**입니다.
실제 학습/변환 설정은 [backend/README.md](backend/README.md)의 "엔진 설정" 참고.

## 테스트

```bash
cd backend && uv run pytest   # 전체 플로우 통합 테스트
cd frontend && npx tsc -b     # 타입체크
```
