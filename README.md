
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
|변형된 실험 프롬프트|300개|
|평가 대상 모델|3개|
|기본 평가 조합|**900회**|

기본 평가 조합은 **60개 요청 × 5개 변형 × 3개 모델**을 기준으로 합니다. 반복 실험 및 방어 기법별 추가 평가는 별도로 집계합니다.

### 데이터셋 출처

본 프로젝트는 [LLM Jailbreak Attack-Defense Arena](https://github.com/ltroin/llm_attack_defense_arena)에서 공개한 Jailbreak 공격 데이터를 참고하여 실험 데이터를 구성합니다. 원본 공격 요청의 `goal` 필드를 기반으로 한국어 표현을 변형하며 **원본 데이터와 본 프로젝트에서 생성한 변형 데이터는 구분**합니다.

* **원본 저장소:** [ltroin/llm_attack_defense_arena](https://github.com/ltroin/llm_attack_defense_arena)
* **저장소 데이터 폴더:** [Data](https://github.com/ltroin/llm_attack_defense_arena/tree/master/Data)



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
