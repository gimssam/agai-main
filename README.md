# agai
agentic ai 한국기술교육대학교 수강생 제공용

# 실습 환경 준비하기  

## 한 줄 요약

1강부터 모든 실습은 **`agentic`라는 파이썬 가상환경**에서 돌아갑니다. 이 절에서 **미니콘다 설치 → `agentic` 환경 생성 → 라이브러리 설치 → API 키 등록**까지 **딱 한 번** 해두면, 이후 30강 내내 `conda activate agentic` 한 줄로 바로 실습을 시작할 수 있습니다.

이 안내는 **Windows + Git Bash**를 기준으로 합니다(macOS·Linux 사용자는 각 단계의 *(macOS/Linux)* 메모를 보세요).

---

## 0. 준비물 체크

시작 전에 세 가지만 준비하면 됩니다.

1. **구글 계정** — Gemini API 키를 무료로 발급받는 데 씁니다(아래 4단계).
2. **이 과정의 실습 코드 폴더** — `code/`, `data/`, `.env.example`, `requirements.txt`가 들어 있는 프로젝트 폴더입니다. 이미 내려받으셨다면 그 폴더 안에서 진행합니다.
   - **폴더 이름은 자유롭게** 지어도 됩니다(`ai-agent`, `agentic-study` 등). 코드가 경로를 *폴더 위치 기준으로 자동 계산*하기 때문에, 이름이 무엇이든 상관없습니다. **윈도우 `문서(Documents)` 폴더 안**에 두는 걸 권합니다. 예: `C:\Users\사용자명\Documents\agentic-study\`.
   - 단, **폴더 안의 구조**(`code/`·`data/`·`.env`·`requirements.txt`)는 그대로 유지하고, 폴더 *이름*에는 **공백·한글을 피해** 영문·하이픈(`-`)으로 짓는 걸 권합니다(일부 도구가 공백 경로에서 말썽을 일으킬 수 있음).
3. **VS Code(편집기)** — 이 과정의 모든 실습은 **VS Code**에서 합니다. 코드 작성도, 실행(터미널)도 VS Code 한 곳에서 끝냅니다. 설정은 아래 「1-2. VS Code 준비」에서 안내합니다.

```text
프로젝트폴더/
├─ code/            ← py 파일들
├─ data/            ← 실습용 CSV·문서
├─ .env.example     ← API 키 양식 (이걸 복사해서 .env 를 만듦)
└─ requirements.txt ← 설치할 라이브러리 목록
```

---

## 1. 미니콘다 설치

**미니콘다(Miniconda)** 는 파이썬과 "가상환경"을 손쉽게 관리해 주는 도구입니다. 가상환경은 **이 과정 전용 파이썬 방**이라고 생각하세요. 다른 프로젝트와 라이브러리가 뒤섞이지 않게 격리해 줍니다.

### (Windows)

1. 설치 파일 다운로드: <https://www.anaconda.com/download/success> → **Miniconda** 항목의 Windows 64-bit 설치 파일.
2. 설치 마법사를 실행하고 기본값으로 진행합니다(설치 경로 예: `C:\Users\사용자명\miniconda3`).
3. 설치 후, 시작 메뉴에서 **Git Bash**를 엽니다. 만약 Git Bash에서 `conda` 명령이 인식되지 않으면 아래 한 줄을 실행합니다.

```bash
# Git Bash에서 conda 를 인식 못 할 때 (한 번만)
source ~/miniconda3/etc/profile.d/conda.sh
```

> Git이 없다면 먼저 Git을 설치하세요(<https://git-scm.com/download/win>). 설치 시 함께 들어오는 **Git Bash**를 이 과정의 터미널로 씁니다.

### (macOS/Linux)

같은 다운로드 페이지에서 OS에 맞는 설치 스크립트를 받아 실행하거나, Homebrew를 쓴다면 `brew install --cask miniconda` 후 `conda init bash`(또는 `zsh`)를 한 번 실행합니다.

### 설치 확인

```bash
conda --version
# conda 24.x.x  처럼 버전이 보이면 설치 성공
```

## 2. `agentic` 가상환경 만들기

이 과정 전용 파이썬 방을 만듭니다. 파이썬 버전은 **3.10**으로 고정합니다(라이브러리 호환성 확보).

```bash
# agentic 이라는 이름으로, 파이썬 3.10 환경 생성
conda create -n agentic python=3.10 -y

# 만든 환경으로 들어가기(활성화)
conda activate agentic
```

활성화에 성공하면 터미널 프롬프트 맨 앞에 **`(agentic)`** 이 붙습니다.

```text
(agentic) 사용자명@PC MINGW64 ~/프로젝트폴더
```

> 이 `(agentic)` 표시가 **"지금 이 방 안에 있다"**는 신호입니다. 앞으로 실습할 때마다 이 표시가 떠 있는지 먼저 확인하세요. 터미널을 새로 열면 표시가 사라지므로, 그때마다 `conda activate agentic`을 다시 실행하면 됩니다.




---

## 3. VS Code 준비  

이 과정의 실습은 모두 **VS Code**에서 합니다. 

### (1) 설치

- 다운로드: <https://code.visualstudio.com> → OS에 맞는 설치 파일로 설치.

### (2) 프로젝트 폴더 열기

VS Code를 켜고 **File → Open Folder…**(폴더 열기)로 **프로젝트 폴더**(즉 `code/`·`data/`가 들어 있는 폴더)를 엽니다. 폴더째로 열어야 `code/common.py` 같은 경로가 제대로 잡힙니다.

### (3) Python 확장 설치

왼쪽 **Extensions(확장)** 아이콘(⊞) → `Python` 검색 → Microsoft의 **Python** 확장 설치. (코드 자동완성·실행·인터프리터 선택에 필요)

### (4) 내장 터미널을 Git Bash로 열기

상단 메뉴 **Terminal → New Terminal**(단축키 `Ctrl + ~`)로 VS Code 안에 터미널을 엽니다. 터미널 우측의 드롭다운(˅)에서 **Git Bash**를 선택하면, 앞으로 모든 `conda`·`pip`·`python` 명령을 이 창에서 실행합니다. (별도 터미널 앱을 따로 열 필요가 없습니다.)

### (5) `agentic` 인터프리터 선택 — 가장 중요

2단계에서 `agentic` 환경을 만든 뒤, VS Code가 그 환경을 쓰도록 지정해야 합니다.

- 단축키 `Ctrl + Shift + P` → **Python: Select Interpreter** 입력 → 목록에서 **`agentic`** 이 들어간 항목 선택.
- 선택하면 VS Code 창 오른쪽 아래(또는 좌하단)에 **`Python 3.10 ('agentic')`** 처럼 표시됩니다.

> 이 인터프리터 선택을 안 하면, VS Code가 엉뚱한 파이썬을 써서 "분명히 설치했는데 `ModuleNotFoundError`"가 납니다. **`agentic`이 선택돼 있는지** 항상 확인하세요. (2단계·3단계를 먼저 끝낸 뒤 이 선택을 하면 됩니다.)

---


## 4. 실습 라이브러리 설치

이 과정에서 쓰는 라이브러리는 `requirements.txt`에 정리돼 있습니다. **프로젝트 폴더 안에서**(즉 `requirements.txt`가 보이는 위치에서) 한 번에 설치합니다.

```bash
# (agentic) 환경이 켜진 상태에서, 프로젝트 폴더 안에서 실행
pip install -r requirements.txt
```

설치되는 주요 라이브러리(미리 알아둘 필요는 없고, 각 강에서 다시 설명합니다):

| 묶음 | 라이브러리 | 쓰는 강 |
|------|-----------|---------|
| LLM SDK | `google-genai`, `openai` | 1~2강 |
| 프레임워크 | `langchain`, `langgraph` 계열 | 5강~ |
| RAG·벡터DB | `faiss-cpu`, `chromadb`, `pypdf` | 13~18강 |
| 웹 검색 | `ddgs` (키 불필요) | 9·22강 |
| 데이터·시각화 | `pandas`, `numpy`, `matplotlib`, `scikit-learn` | 10·11·24강 |
| 환경설정 | `python-dotenv`, `pyyaml` | 전 강 공통 |


---

## 5. Gemini API 키 발급 & `.env` 설정

이 과정의 두뇌는 구글 **Gemini**입니다(무료 티어로 충분합니다). 키를 발급받아 `.env` 파일에 넣습니다.

### 5-1. 키 발급

1. <https://aistudio.google.com/apikey> 접속 → 구글 계정 로그인.
2. **Create API key** 클릭 → 생성된 키(`AIza...` 형태)를 복사합니다.

### 5-2. `.env` 파일 만들기

프로젝트에는 양식 파일 `.env.example`이 들어 있습니다. 이걸 복사해 `.env`를 만든 뒤 키를 채웁니다.

```bash
# 프로젝트 폴더 안에서
cp .env.example .env
```

그다음 `.env` 파일을 편집기로 열어, `GOOGLE_API_KEY` 값을 방금 복사한 키로 바꿉니다.

```bash
# .env 파일 내용 (이렇게 바꿉니다)
GOOGLE_API_KEY=AIza...여기에_본인_키...

# 아래 둘은 선택 — OpenAI는 일부 보조 실습에서만 씁니다. 비워둬도 대부분 진행됩니다.
OPENAI_API_KEY=여기에_본인의_OPENAI_API_키
GEMINI_MODEL=gemini-2.5-flash
```


---

## 6. 설치가 잘 됐는지 확인

마지막으로, 모든 게 제대로 연결됐는지 한 줄로 점검합니다. 이 과정의 공통 도우미 `code/common.py`를 직접 실행하면 됩니다.

```bash
# (agentic) 환경, 프로젝트 폴더 안에서
python code/common.py
```

**이렇게 나오면 성공입니다.**

```text
ROOT : C:\Users\사용자명\Documents\agentic-study
DATA : C:\Users\사용자명\Documents\agentic-study\data (존재: True )
GEMINI_MODEL : gemini-2.5-flash
키 로드 상태 — GOOGLE_API_KEY: True / OPENAI_API_KEY: False
```

> 위 `ROOT`·`DATA` 경로는 **본인이 폴더를 만든 위치/이름에 따라 다르게** 나옵니다. 예시는 `문서(Documents)` 안에 `agentic-study`라는 이름으로 만든 경우입니다(한글 윈도우라도 실제 경로는 `문서`가 아니라 **`Documents`**로 찍힙니다). 경로 글자 자체보다, **`(존재: True )`** 와 아래 **키 로드 상태**가 맞는지를 보세요.

핵심은 마지막 줄의 **`GOOGLE_API_KEY: True`** 입니다. 이게 `True`면 키가 정상적으로 읽힌 것이고, 이제 1강 실습을 시작할 준비가 끝났습니다. (`OPENAI_API_KEY: False`는 정상입니다 — 선택 사항이니까요.)

만약 `GOOGLE_API_KEY: False`가 나오면, 4단계로 돌아가 `.env` 파일에 키가 제대로 들어갔는지 확인하세요.

---

## 7. 승승장구몰 실습 데이터 둘러보기

이 과정의 모든 예제는 가상의 쇼핑몰 **승승장구몰**을 무대로 합니다. 그 데이터는 전부 **`data/` 폴더**에 들어 있습니다. 지금 외울 필요는 전혀 없고, "이런 게 들어 있구나" 정도만 훑어 두세요. 각 강에서 그때그때 필요한 파일을 다시 안내합니다.

### 7-1. 표 형식 데이터 (`data/*.csv`)


> CSV 파일들은 한글 깨짐 방지를 위해 **BOM이 포함된 UTF-8**로 저장돼 있습니다. pandas로 읽을 때 `encoding="utf-8-sig"`를 쓰면 안전합니다 

### 7-2. 문서·기타 데이터

| 파일/폴더 | 내용 | 주로 쓰는 강 |
|-----------|------|--------------|
| `data/docs/환불교환정책.pdf` | 환불·교환 규정 문서 | 13·16·18강(RAG) |
| `data/docs/멤버십정책.pdf` | 멤버십 등급·혜택 문서 | 13·16·17강(RAG) |
| `data/docs/직원핸드북.pdf` | 사내 업무 안내 | 13~18강(RAG) |
| `data/docs/제품매뉴얼_로봇청소기.pdf` | 제품 사용 설명서 | 13~18강(RAG) |
| `data/docs/제품매뉴얼_스마트워치.pdf` | 제품 사용 설명서 | 13~18강(RAG) |


> `data/docs/`의 PDF들은 13강부터 시작하는 **RAG(문서 검색)** 실습의 "사내 문서" 역할을 합니다. "환불 규정이 뭐예요?" 같은 질문에 LLM이 지어내지 않고 **이 문서를 근거로** 답하게 만드는 게 목표죠.

---

## 핵심 정리

- 모든 실습은 **`agentic` 가상환경**에서 돌아갑니다. 이 절에서 **딱 한 번** 만들어 둡니다.
- 순서: **미니콘다 설치 → `conda create -n agentic python=3.10` → `conda activate agentic` → `pip install -r requirements.txt` → `.env`에 `GOOGLE_API_KEY` 등록**.
- 점검: `python code/common.py` 실행 시 **`GOOGLE_API_KEY: True`** 가 보이면 준비 완료.
- 앞으로 터미널을 새로 열 때마다 **`conda activate agentic`** 한 줄이면 바로 실습을 시작할 수 있습니다.

