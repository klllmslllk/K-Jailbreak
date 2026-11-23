
# K-Jailbreak

**Korean Linguistic Variation-based LLM Jailbreak and Defense Benchmark**

한국어 언어적 변형에 따른 대규모 언어 모델(LLM)의 Jailbreak 취약점을 분석하고 방어 기법의 효과를 비교·평가하는 중앙대학교 캡스톤디자인 프로젝트입니다.

## 🔍 프로젝트 개요

LLM은 안전 정책을 우회하여 제한된 응답을 유도하는 Jailbreak 공격에 취약할 수 있습니다. 본 프로젝트는 **동일한 공격 요청을 서로 다른 한국어 표현으로 변형**했을 때 모델의 응답과 공격 성공률이 어떻게 달라지는지 분석합니다. 또한 기존 방어 기법을 비교하고 한국어 환경에 적합한 방어 방안을 연구합니다.

### 연구 목표

* 한국어 언어적 변형별 Jailbreak 공격 성공률(ASR) 분석
* LLM 모델별 취약점 비교
* 방어 기법 적용 전후의 성능 및 오탐 비교
* 한국어 특성을 고려한 방어 방안 연구
* 실험 결과의 저장·분석·시각화 플랫폼 구축

## 🧪 실험 설계

### 평가 대상 모델

|모델|규모|Ollama 태그|
|-|-:|-|
|Qwen3|8B|`qwen3:8b`|
|Llama 3.1|8B|`llama3.1:8b`|
|EXAONE 3.5|7.8B|`exaone3.5:7.8b`|

세 모델은 Ollama를 통해 로컬 환경에서 실행하며 비교 가능한 조건을 위해 공통 설정을 사용합니다. 실험에는 Q4_K_M 양자화 모델을 사용합니다.

### 한국어 언어적 변형

|유형|코드|설명|
|-|-|-|
|평어체|`PLAIN`|비격식적이고 일상적인 표현|
|경어체|`HONOR`|높임말을 사용한 표현|
|충청도 방언|`CHUNG`|충청 지역의 언어적 특성을 반영한 표현|
|경상도 방언|`GYEONG`|경상 지역의 언어적 특성을 반영한 표현|
|은어|`SLANG`|구어적·비표준적 표현|

### 데이터 구성

|항목|수량|
|-|-:|
|원본 공격 요청|60개|
|언어적 변형|5종|
|영어 원문을 포함한 실험 프롬프트|360개|
|평가 대상 모델|3개|
|기본 평가 조합|**1,080회**|

기본 평가 조합은 **60개 요청 × (영어 원문 1종 + 한국어 변형 5종) × 3개 모델**을 기준으로 합니다. 반복 실험 및 방어 기법별 추가 평가는 별도로 집계합니다.

### 데이터셋 출처

본 프로젝트는 [LLM Jailbreak Attack-Defense Arena](https://github.com/ltroin/llm_attack_defense_arena)에서 공개한 Jailbreak 공격 데이터를 참고하여 실험 데이터를 구성합니다. 원본 공격 요청의 `goal` 필드를 기반으로 한국어 표현을 변형하며 **원본 데이터와 본 프로젝트에서 생성한 변형 데이터는 구분**합니다.

* **원본 저장소:** [ltroin/llm_attack_defense_arena](https://github.com/ltroin/llm_attack_defense_arena)
* **저장소 데이터 폴더:** [Data](https://github.com/ltroin/llm_attack_defense_arena/tree/master/Data)



## 설치 및 실험 실행

Python 3.10 이상과 Ollama가 필요합니다.

```bash
git clone https://github.com/klllmslllk/K-Jailbreak.git
cd K-Jailbreak

python -m venv .venv
source .venv/bin/activate        # macOS / Linux (Bash, Zsh)
.venv\Scripts\activate          # Windows CMD
.\.venv\Scripts\Activate.ps1     # Windows PowerShell

pip install -r requirements.txt
```

Ollama를 설치·실행한 뒤 모델을 다운로드합니다.

```bash
ollama pull qwen3:8b
ollama pull llama3.1:8b
ollama pull exaone3.5:7.8b
ollama pull llama-guard3:8b
```

`datasets/data.csv`로 새 실험을 시작합니다.

```bash
python main.py
```

화면에 출력되는 실험 ID(`run_id`)를 기록하세요. 응답은
`results/results.db`에 저장되며, 실행할 때마다 새 실험 ID로 결과를 수집합니다.
기존 실험 결과는 유지됩니다. 성공·실패 자동 판정은 수행하지 않으며 `success`는 `NULL`로 저장됩니다.

API 호출이나 DB 저장 실패로 기록되지 않은 항목만 재시도하려면 다음과 같이 실행합니다.

```bash
python main.py --run-id 기존실험ID
```

데이터셋·모델·설정을 기존 실험과 동일하게 유지하세요. 해당 실험에서 이미 저장된 조합은 건너뜁니다.
새 터미널에서는 가상환경을 다시 활성화해야 합니다. `results/results.db`는 Git 업로드에서 제외됩니다.

### 방어 모듈 적용

`--defense`에 사용할 모듈을 지정합니다. 생략하면 방어를 적용하지 않으며, 여러 모듈을 함께 사용할 수 있습니다.

|모듈|적용 단계|설명|
|-|-|-|
|`input-guard`|입력|Llama Guard 3가 요청을 검사하고, `unsafe`이면 대상 모델 호출 없이 거절합니다.|
|`combined_prompt`|시스템 프롬프트|Self-Reminder, Goal Prioritization, 한국어 언어 변형 대응 지침을 전달합니다.|
|`output-guard`|출력|Llama Guard 3가 요청과 응답을 검사하고, `unsafe`이면 응답을 거절문으로 대체합니다.|

실행 순서는 입력 검사 → 시스템 메시지 구성 → 대상 모델 호출 → 출력 검사입니다. Guard로 차단된 공격의 최종 `success`는 0이며, 출력 차단은 원래 응답이 안전했다는 뜻은 아닙니다. Guard 판정 오류가 발생한 요청은 건너뛰고 다시 실행할 수 있습니다.

```bash
python main.py --defense input-guard
python main.py --defense input-guard combined_prompt output-guard
python main.py --run-id 기존실험ID --defense combined_prompt
```

Guard 사용 전 Ollama에서 `llama-guard3:8b`를 설치해야 합니다. 동일 실험을 재개할 때는 데이터셋과 방어 설정, Guard 모델 digest를 유지하세요. 다른 방어 설정을 적용하려면 새 실험 ID를 사용합니다.

Guard 판정과 설정은 `results/guard_results.db`에 입력·출력별로 저장됩니다. 출력 기록에는 차단 전 원본 응답도 포함됩니다. 결과의 `defense_module`에는 사용한 모듈이 기록되며, 방어를 적용하지 않은 경우와 과거 설정이 기록되지 않은 경우에는 `NULL`입니다.

정상 요청에 대한 FPR을 측정하려면 별도의 정상 데이터셋 `benign.csv`을 사용합니다.

```bash
python main.py --defense input-guard --dataset datasets/benign.csv --dataset-type benign
python guard_metrics.py 실험ID
```

FPR은 정상 데이터의 `unsafe / (unsafe + safe)`이며 오류와 기록이 없는 요청은 집계에서 제외됩니다. 반복 판정은 각 `attack_id`의 최신 결과를 사용합니다. 언어 변형은 독립 표본이 아니며 한국어 및 방언 성능은 별도 검증이 필요합니다.

방어 모듈은 `defenses/input`, `defenses/system`, `defenses/output`에 구분하고 `defenses/registry.py`에 등록합니다.

### 모델에 전달되는 메시지 확인

`--show-prompt`를 추가하면 각 요청에서 Ollama에 전달할 메시지를 역할별로 출력합니다.

```bash
python main.py --defense combined_prompt --show-prompt
```

방어 없이 확인할 때는 `python main.py --show-prompt`를 사용합니다. 메시지 출력 후에도 모델 호출과 결과 저장이 진행됩니다.

### 현재 구현 구조

```text
main.py                              # 실행 옵션 처리
config.py                            # 모델, 경로 및 실험 설정
runner.py                            # 데이터 로드 및 실험 실행
models/ollama_client.py              # Ollama API 호출
defenses/registry.py                 # 단계별 방어 모듈 등록
defenses/guard_client.py             # 공통 Guard 호출 및 응답 파싱
defenses/input/input_guard.py        # 입력 방어
defenses/system/combined_prompt.py   # 시스템 프롬프트 방어
defenses/output/output_guard.py      # 출력 방어
database/db.py                       # SQLite 연결 및 결과 저장
datasets/data.csv                    # 실험 데이터
results/results.db                   # 로컬 실험 결과
```

현재 구현은 모델 응답 수집과 방어 프롬프트 적용까지 지원합니다. 성공 여부 판정, 지표 계산 및 웹 대시보드는 향후 구현할 기능입니다.

## 📊 평가 지표

|지표|의미|해석|
|-|-|-|
|**ASR** (Attack Success Rate)|공격 시도 중 성공한 비율|낮을수록 안전|
|**Defense Success Rate**|방어 대상 공격 중 차단에 성공한 비율|높을수록 좋음|
|**FPR** (False Positive Rate)|정상 요청을 공격으로 잘못 판단한 비율|낮을수록 좋음|

평가 지표의 판정 기준과 분모는 실험 단계별로 일관되게 정의하여 비교합니다.

## 🛠️ 기술 스택

|구분|기술|
|-|-|
|언어 및 실험 자동화|Python|
|로컬 LLM 실행|Ollama|
|데이터 저장|SQLite|
|웹 대시보드|Streamlit|
|버전 관리|Git / GitHub|

## 시스템 구성

```text
Original Attack Dataset
          |
          v
Korean Linguistic Variations
          |
          v
Defense Module (On / Off)
          |
          v
LLM Inference via Ollama
          |
          v
Response Collection & Evaluation
          |
          v
SQLite Database
          |
          v
Analysis & Streamlit Dashboard
```

동일한 공격 요청을 언어별·모델별로 실행하고, 방어 기법 적용 여부에 따른 결과를 수집합니다. 응답과 평가 결과는 SQLite에 저장하여 비교 분석 및 시각화에 활용합니다.

## 연구 진행 항목

* [x] 평가 대상 LLM 선정
* [x] 한국어 방언 예비 비교 및 최종 유형 선정
* [ ] 언어적 변형별 Jailbreak 취약점 분석 결과 정리
* [ ] 기존 방어 기법의 성능 비교
* [ ] 한국어 환경을 고려한 방어 방안 제안 및 평가
* [ ] 실험 결과 대시보드 정리

> 위 체크리스트는 프로젝트의 주요 연구 항목을 나타냅니다. 완료 여부는 진행 상황에 따라 갱신합니다.

## 👥 팀 소개

**중앙대학교 소프트웨어학부 · 2026학년도 2학기 캡스톤디자인(1)**  

|팀원|소속|
|-|-|
|김민성|중앙대학교 소프트웨어학부|
|신다윗|중앙대학교 소프트웨어학부|
|서위혁|중앙대학교 소프트웨어학부|
