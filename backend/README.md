# Revoice Backend

AI 커버곡 생성 서비스 백엔드. 학습 기반 RVC(Applio) 파이프라인:
**보컬 분리(RoFormer) → 음성 변환(RVC) → 믹싱(ffmpeg)**

## 실행

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- 테스트: `uv run pytest`

## 구조 (Feature-Driven)

```
app/
  core/        # 설정, DB 세션, 도메인 예외
  features/    # 기능 단위 수직 슬라이스
    voices/    #   보이스 모델 + 데이터셋 관리
    trainings/ #   학습 잡 시작/모니터링
    covers/    #   커버 생성 파이프라인 + 다운로드
    └─ 각 feature: models / schemas / crud / service / router
  engines/     # 오디오 엔진 추상화 (Protocol) + mock/applio 구현
  jobs/        # 백그라운드 잡 러너
  storage/     # 파일 저장 레이아웃
```

계층 규칙: `router → service → crud` 단방향. 쿼리는 crud에만, 비즈니스 로직은
service에만, router는 얇게 유지.

## 엔진 설정

`mock`(개발용, GPU 불필요)과 `applio`(실제 학습/변환) 엔진을 `.env`로 전환한다.
이 저장소에는 이미 실제 엔진이 셋업되어 있음 (`.env` 참고):

```env
REVOICE_ENGINE=applio
REVOICE_APPLIO_DIR=.../backend/vendor/applio          # Applio 체크아웃 (gitignore됨)
REVOICE_APPLIO_PYTHON=.../vendor/applio/.venv/Scripts/python.exe
REVOICE_SEPARATOR_BIN=~/.local/bin/audio-separator.exe # uv tool install "audio-separator[cpu]"
REVOICE_TRAINING_BATCH_SIZE=4
```

새 환경에서 다시 셋업하는 절차:

1. `git clone --depth 1 https://github.com/IAHispano/Applio backend/vendor/applio`
2. Applio 전용 venv 생성 후 CPU torch + 의존성 설치
   (`requirements.txt`의 `+cu128` 고정을 CPU 빌드로 대체, `torchcrepe`/`torchfcpe` 포함 주의)
3. `python core.py prerequisites --pretraineds_hifigan True --models True --exe False`
   → pretrained HiFi-GAN, rmvpe, contentvec 다운로드 (~1.7GB)
4. `uv tool install "audio-separator[cpu]"` + `ffmpeg` PATH 확인

알아둘 것:

- **CPU 학습은 매우 느리다** (이 머신 기준 1 epoch ≈ 1분+). 파이프라인 확인은 3~10 epoch,
  실제 품질(200 epoch+)은 NVIDIA GPU 환경 권장.
- Applio `core.py`는 실패해도 exit code 0으로 끝나므로, 엔진은 각 단계의 산출물
  (sliced_audios / extracted / *.pth / *.index) 존재를 검증해 성공을 판정한다.
- `assets/config.json`이 없으면 가중치 추출이 조용히 실패한다 — 엔진이 학습 시작 시
  템플릿에서 자동 생성한다.
- 학습 진행률은 Applio 출력의 epoch 기록과 배치 tqdm을 스트리밍 파싱해 DB에 기록된다.
  보컬 분리(audio-separator)는 파이프에서 tqdm을 비활성화해 진행률 신호가 없다
  (UI는 단계 라벨 + 불확정 바로 표시).

## API 요약

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/voices` | 보이스 생성 |
| POST | `/api/v1/voices/{id}/dataset` | 데이터셋 오디오 업로드 (multipart) |
| POST | `/api/v1/trainings` | 학습 시작 (202, 백그라운드) |
| GET | `/api/v1/trainings/{id}` | 학습 진행률/상태 |
| POST | `/api/v1/covers` | 커버 생성 (곡 업로드, 202) |
| GET | `/api/v1/covers/{id}` | 커버 진행률/상태 |
| GET | `/api/v1/covers/{id}/audio` | 완성본 다운로드 |
