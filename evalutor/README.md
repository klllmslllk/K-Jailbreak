# Qwen 이진 평가기 사용법

저장소 루트에서 Ollama 서버를 실행하고 필요한 모델과 패키지를 설치합니다.

```powershell
ollama pull qwen3.5:9b
python -m pip install -r requirements.txt
```

저장된 공격 응답을 평가합니다.

```powershell
python -m evalutor.cli
```

자주 사용하는 옵션은 다음과 같습니다.

```powershell
# 평가 대상 건수만 확인
python -m evalutor.cli --dry-run

# 앞에서부터 최대 10건 평가
python -m evalutor.cli --limit 10

# 특정 실행만 평가
python -m evalutor.cli --run-id RUN_ID

# 특정 실행의 평가 오류를 재시도하고 미평가 항목 평가
python -m evalutor.cli --run-id RUN_ID --resume
```

`RUN_ID`를 실제 실행 ID로 바꾸세요. 같은 입력과 설정으로 완료된 항목은 건너뜁니다. `--resume`은 정상 판정인 `FAILURE`를 재평가하지 않습니다.

기본 입력은 `results/results.db`와 `results/guard_results.db`이며, 결과는 `results/evaluation_results.db`에 저장됩니다. 경로는 `--source-db`, `--guard-db`, `--output-db`로 변경할 수 있습니다. Guard DB에 공격 데이터(`attack`)로 기록된 실행만 평가합니다.

Python에서 직접 평가할 수도 있습니다.

```python
from evalutor import evaluate, EvaluationError

try:
    result = evaluate("질문", "모델의 응답")
    print(result)  # SUCCESS: 1, FAILURE: 0
except EvaluationError as error:
    print(error)
```
