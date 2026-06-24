# -*- coding: utf-8 -*-
"""
rag_chatbot.py — 문서 기반 RAG 챗봇 (Streamlit UI)

실행: python -m streamlit run rag_chatbot.py
지원 문서: data/docs/ 아래 PDF 전체를 자동 색인
"""

import os
import pathlib
from dotenv import load_dotenv

# 프로젝트 루트 경로 (.env, data/ 등 기준점)
ROOT = pathlib.Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")  # .env 파일에서 환경변수 로드

import streamlit as st

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="문서 기반 RAG 챗봇",
    page_icon="📚",
    layout="wide",
)

# ── 상수 ─────────────────────────────────────────────────────────────────────
DOCS_DIR = ROOT / "data" / "docs"   # PDF 문서 폴더 경로

CHUNK_SIZE = 500        # 문서를 나누는 청크 크기 (글자 수)
CHUNK_OVERLAP = 50      # 청크 간 겹치는 글자 수 (문맥 손실 방지)
TOP_K = 4               # 검색 시 가져올 유사 청크 개수

# 사용할 Gemini 모델 (.env에서 덮어쓸 수 있음)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/gemini-embedding-001")

# LLM에게 전달하는 역할·답변 규칙 지침
SYSTEM_PROMPT = """너는 회사 내부 문서를 기반으로 정보를 안내하는 친절한 AI 상담원이다.

답변 규칙:
1. 반드시 제공된 문서 내용(context)을 근거로 답하라.
2. 문서에 없는 내용은 "해당 내용은 문서에서 찾을 수 없습니다."라고 솔직히 말하라.
3. 답변 끝에 어떤 문서를 참고했는지 출처를 밝혀라. (예: 📄 출처: 환불교환정책.pdf p.2)
4. 친절하고 명확한 한국어로 답하라.
"""

# ── 헬퍼 함수 ────────────────────────────────────────────────────────────────

def require_google_key():
    """GOOGLE_API_KEY가 없으면 안내 메시지 표시 후 앱 중단"""
    key = os.getenv("GOOGLE_API_KEY", "")
    if not key or key.startswith("여기에"):
        st.error(
            "❌ GOOGLE_API_KEY가 설정되지 않았습니다.\n\n"
            "1. `.env.example`을 복사해 `.env`로 저장\n"
            "2. `.env` 파일에 `GOOGLE_API_KEY=발급받은키` 입력\n"
            "3. 앱 재시작"
        )
        st.stop()


@st.cache_resource(show_spinner="📚 문서를 읽고 벡터 인덱스를 구축하는 중...")
def build_vectorstore():
    """
    PDF → 청크 분할 → 임베딩 → FAISS 색인 파이프라인
    @st.cache_resource: 앱이 살아있는 동안 최초 1회만 실행 (재질문 시 재사용)
    """
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    require_google_key()

    # DOCS_DIR 안의 PDF 파일 목록 수집
    pdf_files = sorted(DOCS_DIR.glob("*.pdf"))
    if not pdf_files:
        st.error(f"❌ {DOCS_DIR} 에 PDF 파일이 없습니다.")
        st.stop()

    # ① PDF 로드: 각 페이지를 Document 객체로 변환
    all_docs = []
    for pdf in pdf_files:
        pages = PyPDFLoader(str(pdf)).load()
        for page in pages:
            page.metadata["source_name"] = pdf.name   # 출처 표시용 파일명 저장
        all_docs.extend(pages)

    # ② 청크 분할: 긴 페이지를 검색 단위(chunk)로 잘게 나눔
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],  # 단락 → 줄 → 단어 순으로 분리
    )
    chunks = splitter.split_documents(all_docs)

    # ③ 임베딩 & FAISS 색인: 청크를 벡터로 변환해 유사도 검색 가능하게 저장
    embeddings = GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBED_MODEL,
        output_dimensionality=768,   # 3072차원을 768로 압축 (속도·메모리 절약)
    )
    vectorstore = FAISS.from_documents(chunks, embeddings)

    return vectorstore, [p.name for p in pdf_files], len(chunks)


def format_source(doc) -> str:
    """검색된 청크의 출처를 '파일명 p.페이지' 형식으로 반환"""
    meta = doc.metadata
    name = meta.get("source_name") or pathlib.Path(meta.get("source", "")).name
    page = meta.get("page", "")
    page_str = f" p.{page + 1}" if page != "" else ""  # 0-index → 1-index 변환
    return f"📄 {name}{page_str}"


def retrieve_and_answer(question: str, vectorstore, chat_history: list) -> tuple[str, list]:
    """
    RAG 핵심 파이프라인
      ① 벡터 검색 → ② 컨텍스트 조립 → ③ LLM 호출 → ④ 답변 + 출처 반환
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    # ① 질문과 의미적으로 유사한 청크 Top-K 검색
    docs = vectorstore.similarity_search(question, k=TOP_K)

    # ② 검색된 청크를 하나의 컨텍스트 문자열로 조립
    context_parts = []
    for i, doc in enumerate(docs, 1):
        src = format_source(doc)
        context_parts.append(f"[{i}] {src}\n{doc.page_content}")
    context = "\n\n---\n\n".join(context_parts)

    # ③ 메시지 구성: 시스템 지침 + 최근 대화 이력(최대 6턴) + 현재 질문
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for turn in chat_history[-6:]:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))

    # 현재 질문에 검색된 문서 컨텍스트를 함께 전달
    user_msg = f"""다음 문서 내용을 참고해 질문에 답하라.

=== 참고 문서 ===
{context}

=== 질문 ===
{question}"""
    messages.append(HumanMessage(content=user_msg))

    # ④ Gemini 호출
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.2)
    response = llm.invoke(messages)

    # 중복 출처 제거 후 반환
    sources = list(dict.fromkeys(format_source(d) for d in docs))
    return response.content, sources


# ── Streamlit UI ──────────────────────────────────────────────────────────────

def main():
    # 제목 클릭 시 /?reset=true 로 이동 → 대화 초기화 후 첫 화면으로 리다이렉트
    if st.query_params.get("reset"):
        st.session_state.messages = []
        st.query_params.clear()
        st.rerun()

    # ── 사이드바 ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("📚 RAG 챗봇")
        st.caption("문서 기반 정보 검색 챗봇")
        st.divider()

        # .env가 없을 때 UI에서 직접 API 키를 입력할 수 있는 보조 수단
        api_key_input = st.text_input(
            "Google API Key (선택)",
            type="password",
            placeholder=".env 설정시 비워두세요",
        )
        if api_key_input:
            os.environ["GOOGLE_API_KEY"] = api_key_input  # 런타임에 즉시 적용

        st.divider()

        # 색인된 PDF 목록 표시
        if DOCS_DIR.exists():
            st.subheader("📂 색인된 문서")
            for pdf in sorted(DOCS_DIR.glob("*.pdf")):
                st.markdown(f"- {pdf.name}")
        else:
            st.warning(f"`{DOCS_DIR}` 폴더가 없습니다.")

        st.divider()

        # 대화 초기화 버튼
        if st.button("🗑️ 대화 초기화"):
            st.session_state.messages = []
            st.rerun()

    # ── 메인 화면 ─────────────────────────────────────────────────────────────

    # 제목을 링크로 감싸 클릭 시 홈(첫 화면)으로 이동
    st.markdown(
        '<h1><a href="/?reset=true" style="text-decoration:none; color:inherit;">'
        '📚 문서 기반 RAG 챗봇</a></h1>',
        unsafe_allow_html=True,
    )
    st.caption("회사 내부 문서(매뉴얼·정책·핸드북)를 기반으로 정확한 정보를 제공합니다.")

    # 벡터스토어 로드 (캐시 덕분에 두 번째 질문부터는 즉시 반환)
    try:
        vectorstore, doc_names, chunk_count = build_vectorstore()
        st.success(f"✅ {len(doc_names)}개 문서 색인 완료 ({chunk_count:,}개 청크)")
    except SystemExit:
        return
    except Exception as e:
        st.error(f"벡터 인덱스 구축 실패: {e}")
        st.stop()

    # 대화 이력 초기화 (세션 단위로 유지)
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 저장된 대화 이력을 화면에 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📎 참고 문서"):
                    for src in msg["sources"]:
                        st.markdown(src)

    # 대화가 없을 때만 예시 질문 버튼 표시
    if not st.session_state.messages:
        st.markdown("#### 💡 이런 걸 물어보세요")
        example_questions = [
            "환불 신청은 어떻게 하나요?",
            "로봇청소기 필터 청소 방법을 알려주세요",
            "멤버십 등급별 혜택은 무엇인가요?",
            "스마트워치 배터리 교체 주기는?",
            "신입 직원 온보딩 절차를 알려주세요",
        ]
        cols = st.columns(len(example_questions))
        for col, q in zip(cols, example_questions):
            if col.button(q, use_container_width=True):
                # 버튼 클릭 시 pending_question에 저장 → rerun 후 아래에서 처리
                st.session_state.pending_question = q
                st.rerun()

    # 예시 질문 버튼 클릭 or 채팅 입력 중 하나를 user_input으로 통일
    if "pending_question" in st.session_state:
        user_input = st.session_state.pop("pending_question")
    else:
        user_input = st.chat_input("문서에 대해 질문하세요...")

    # 질문이 들어오면 RAG 파이프라인 실행
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("문서에서 관련 내용을 검색하는 중..."):
                try:
                    answer, sources = retrieve_and_answer(
                        user_input,
                        vectorstore,
                        st.session_state.messages[:-1],  # 현재 질문 제외한 이력 전달
                    )
                    st.markdown(answer)
                    if sources:
                        with st.expander("📎 참고 문서"):
                            for src in sources:
                                st.markdown(src)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "sources": sources}
                    )
                except Exception as e:
                    error_msg = f"❌ 오류 발생: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )


if __name__ == "__main__":
    main()
