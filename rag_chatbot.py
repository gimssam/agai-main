# -*- coding: utf-8 -*-
"""
rag_chatbot.py — 문서 기반 RAG 챗봇 (Streamlit UI)

실행: streamlit run rag_chatbot.py
     (agai-main 디렉터리에서 실행)

지원 문서: data/docs/ 아래 PDF 전체를 자동 색인
  - 환불교환정책.pdf
  - 멤버십정책.pdf
  - 제품매뉴얼_로봇청소기.pdf
  - 제품매뉴얼_스마트워치.pdf
  - 직원핸드북.pdf
"""

import sys
import pathlib
import os

# code/ 디렉터리를 import 경로에 추가 (common.py 사용)
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import streamlit as st

# ── 페이지 설정 ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="문서 기반 RAG 챗봇",
    page_icon="📚",
    layout="wide",
)

# ── 상수 ────────────────────────────────────────────────────────────────────
DOCS_DIR = ROOT / "data" / "docs"
FAISS_INDEX_PATH = ROOT / "faiss_index"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 4

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/gemini-embedding-001")

SYSTEM_PROMPT = """너는 회사 내부 문서를 기반으로 정보를 안내하는 친절한 AI 상담원이다.

답변 규칙:
1. 반드시 제공된 문서 내용(context)을 근거로 답하라.
2. 문서에 없는 내용은 "해당 내용은 문서에서 찾을 수 없습니다."라고 솔직히 말하라.
3. 답변 끝에 어떤 문서를 참고했는지 출처를 밝혀라. (예: 📄 출처: 환불교환정책.pdf p.2)
4. 친절하고 명확한 한국어로 답하라.
"""

# ── 헬퍼 함수 ────────────────────────────────────────────────────────────────

def require_google_key() -> str:
    key = os.getenv("GOOGLE_API_KEY", "")
    if not key or key.startswith("여기에"):
        st.error(
            "❌ GOOGLE_API_KEY가 설정되지 않았습니다.\n\n"
            "1. `.env.example`을 복사해 `.env`로 저장\n"
            "2. `.env` 파일에 `GOOGLE_API_KEY=발급받은키` 입력\n"
            "3. 앱 재시작"
        )
        st.stop()
    return key


@st.cache_resource(show_spinner="📚 문서를 읽고 벡터 인덱스를 구축하는 중...")
def build_vectorstore():
    """PDF 전체를 로드 → 청크 분할 → FAISS 색인 (최초 1회, 이후 캐시)"""
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    require_google_key()

    pdf_files = sorted(DOCS_DIR.glob("*.pdf"))
    if not pdf_files:
        st.error(f"❌ {DOCS_DIR} 에 PDF 파일이 없습니다.")
        st.stop()

    # ① 모든 PDF 로드
    all_docs = []
    for pdf in pdf_files:
        pages = PyPDFLoader(str(pdf)).load()
        # 소스 파일명을 메타데이터에 추가
        for page in pages:
            page.metadata["source_name"] = pdf.name
        all_docs.extend(pages)

    # ② 청크 분할
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(all_docs)

    # ③ 임베딩 & FAISS 색인
    embeddings = GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBED_MODEL, output_dimensionality=768
    )
    vs = FAISS.from_documents(chunks, embeddings)

    return vs, [p.name for p in pdf_files], len(chunks)


def format_source(doc) -> str:
    """검색된 문서 청크의 출처 문자열 생성"""
    meta = doc.metadata
    name = meta.get("source_name") or pathlib.Path(meta.get("source", "")).name
    page = meta.get("page", "")
    page_str = f" p.{page + 1}" if page != "" else ""
    return f"📄 {name}{page_str}"


def retrieve_and_answer(question: str, vectorstore, chat_history: list) -> tuple[str, list]:
    """RAG 파이프라인: 검색 → 프롬프트 조립 → LLM 답변 + 출처 반환"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    # ① 관련 청크 검색
    docs = vectorstore.similarity_search(question, k=TOP_K)

    # ② 컨텍스트 조립
    context_parts = []
    for i, doc in enumerate(docs, 1):
        src = format_source(doc)
        context_parts.append(f"[{i}] {src}\n{doc.page_content}")
    context = "\n\n---\n\n".join(context_parts)

    # ③ 메시지 구성 (시스템 + 대화 이력 + 현재 질문)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for turn in chat_history[-6:]:   # 최근 6턴 기억
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))

    user_msg = f"""다음 문서 내용을 참고해 질문에 답하라.

=== 참고 문서 ===
{context}

=== 질문 ===
{question}"""
    messages.append(HumanMessage(content=user_msg))

    # ④ LLM 호출
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.2)
    response = llm.invoke(messages)
    answer = response.content

    # ⑤ 출처 목록
    sources = list(dict.fromkeys(format_source(d) for d in docs))

    return answer, sources


# ── Streamlit UI ─────────────────────────────────────────────────────────────

def main():
    # 홈(첫 화면) 리셋 처리
    if st.query_params.get("reset"):
        st.session_state.messages = []
        st.query_params.clear()
        st.rerun()

    # 사이드바
    with st.sidebar:
        st.title("📚 RAG 챗봇")
        st.caption("문서 기반 정보 검색 챗봇")

        st.divider()

        # API 키 입력 (선택 — .env 없을 때 보조 수단)
        api_key_input = st.text_input(
            "Google API Key (선택)",
            type="password",
            placeholder=".env 설정시 비워두세요",
        )
        if api_key_input:
            os.environ["GOOGLE_API_KEY"] = api_key_input

        st.divider()

        # 문서 목록 & 인덱스 상태
        if DOCS_DIR.exists():
            pdf_list = sorted(DOCS_DIR.glob("*.pdf"))
            st.subheader("📂 색인된 문서")
            for pdf in pdf_list:
                st.markdown(f"- {pdf.name}")
        else:
            st.warning(f"`{DOCS_DIR}` 폴더가 없습니다.")

        st.divider()
        if st.button("🗑️ 대화 초기화"):
            st.session_state.messages = []
            st.rerun()

    # 메인 화면 헤더
    st.markdown(
        '<h1><a href="/?reset=true" style="text-decoration:none; color:inherit;">'
        '📚 문서 기반 RAG 챗봇</a></h1>',
        unsafe_allow_html=True,
    )
    st.caption(
        "회사 내부 문서(매뉴얼·정책·핸드북)를 기반으로 정확한 정보를 제공합니다."
    )

    # 벡터스토어 로드 (캐시됨)
    try:
        vectorstore, doc_names, chunk_count = build_vectorstore()
        st.success(
            f"✅ {len(doc_names)}개 문서 색인 완료 ({chunk_count:,}개 청크)",
            icon="✅",
        )
    except SystemExit:
        return
    except Exception as e:
        st.error(f"벡터 인덱스 구축 실패: {e}")
        st.stop()

    # 대화 이력 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 대화 이력 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📎 참고 문서"):
                    for src in msg["sources"]:
                        st.markdown(src)

    # 예시 질문 버튼 (대화가 없을 때만 표시)
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
                st.session_state.pending_question = q
                st.rerun()

    # 예시 질문 클릭 처리
    if "pending_question" in st.session_state:
        user_input = st.session_state.pop("pending_question")
    else:
        user_input = st.chat_input("문서에 대해 질문하세요...")

    # 질문 처리
    if user_input:
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # RAG 답변 생성
        with st.chat_message("assistant"):
            with st.spinner("문서에서 관련 내용을 검색하는 중..."):
                try:
                    answer, sources = retrieve_and_answer(
                        user_input,
                        vectorstore,
                        st.session_state.messages[:-1],
                    )
                    st.markdown(answer)
                    if sources:
                        with st.expander("📎 참고 문서"):
                            for src in sources:
                                st.markdown(src)
                    # 이력 저장
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
