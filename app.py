import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import streamlit as st
from dotenv import load_dotenv
from rag_chain import build_chain

load_dotenv()

# ── Content ──────────────────────────────────────────────────────────────────
# Existing sample questions are preserved exactly.
SAMPLE_QUESTIONS = [
    "Why is my mobile internet so slow?",
    "My calls keep dropping — what should I do?",
    "How do I activate international roaming?",
    "Why is my bill higher than usual this month?",
    "My phone shows SIM not detected after a restart",
    "How do I enable Wi-Fi calling?",
    "I was charged for roaming but had a bundle active",
    "How do I unlock my phone for another network?",
]

# Sidebar quick-help topics → question sent through the existing RAG chain.
QUICK_HELP = [
    ("📶  Mobile Internet", SAMPLE_QUESTIONS[0]),
    ("📞  Dropped Calls", SAMPLE_QUESTIONS[1]),
    ("🌍  International Roaming", SAMPLE_QUESTIONS[2]),
    ("💳  Billing", SAMPLE_QUESTIONS[3]),
    ("📱  SIM Issues", SAMPLE_QUESTIONS[4]),
    ("📡  Wi-Fi Calling", SAMPLE_QUESTIONS[5]),
]

st.set_page_config(
    page_title="Telecom Support Chat",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ──────────────────────────────────────────────────────────────────
# Colors/fonts come from .streamlit/config.toml; this CSS only adds polish.
STYLE = """
<style>
:root {
  --accent: #5B8CFF;
  --accent-soft: rgba(91, 140, 255, 0.12);
  --border: #26324F;
  --surface: #121A30;
  --muted: #8A96B5;
}

/* Layout: centered reading column, comfortable padding on small screens */
.block-container { max-width: 860px; padding-top: 2rem; padding-bottom: 6rem; }
@media (max-width: 640px) { .block-container { padding-left: 1rem; padding-right: 1rem; } }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* Header */
.hero { display: flex; justify-content: space-between; align-items: flex-start;
        gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem;
        padding-bottom: 1.25rem; border-bottom: 1px solid var(--border); }
.hero-brand { color: var(--accent); font-weight: 600; font-size: 0.9rem; margin-bottom: 0.35rem; }
.hero h1 { margin: 0; padding: 0; font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; }
.hero p { margin: 0.4rem 0 0; color: var(--muted); font-size: 1rem; }
.pill { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0.75rem;
        border: 1px solid var(--border); border-radius: 999px; background: var(--surface);
        color: var(--muted); font-size: 0.8rem; white-space: nowrap; }
.pill .dot { width: 8px; height: 8px; border-radius: 50%; background: #34D399;
             box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.18); }

/* Welcome */
.welcome { text-align: center; margin: 2.5rem 0 1.5rem; }
.welcome h2 { font-size: 1.7rem; font-weight: 650; margin: 0 0 0.4rem; letter-spacing: -0.01em; }
.welcome p { color: var(--muted); margin: 0; }

/* Buttons (sidebar quick help + suggestion cards) */
.stButton > button {
  justify-content: flex-start; text-align: left; width: 100%;
  border: 1px solid var(--border); border-radius: 14px; background: var(--surface);
  padding: 0.75rem 1rem; min-height: 3rem; transition: border-color .15s, background .15s;
}
.stButton > button:hover { border-color: var(--accent); background: var(--accent-soft); color: inherit; }
.stButton > button[kind="primary"] {
  justify-content: center; background: var(--accent); border-color: var(--accent);
  color: #0B1020; font-weight: 600;
}
.stButton > button[kind="primary"]:hover { filter: brightness(1.08); background: var(--accent); }

/* Sidebar */
section[data-testid="stSidebar"] { border-right: 1px solid var(--border); }
.brand { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.25rem; }
.brand-logo { width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center;
              font-size: 1.3rem; background: var(--accent-soft); border: 1px solid var(--accent); }
.brand-name { font-weight: 700; font-size: 1.1rem; line-height: 1.2; }
.brand-sub { color: var(--muted); font-size: 0.85rem; margin: 0.5rem 0 1.25rem; }
.side-label { color: var(--muted); font-size: 0.85rem; font-weight: 600; margin: 1.25rem 0 0.5rem; }
.side-footer { color: var(--muted); font-size: 0.78rem; margin-top: 1.5rem; padding-top: 1rem;
               border-top: 1px solid var(--border); display: flex; align-items: center; gap: 0.5rem; }
.side-footer .dot { width: 7px; height: 7px; border-radius: 50%; background: #34D399; }

/* Chat messages */
div[data-testid="stChatMessage"] {
  border: 1px solid var(--border); border-radius: 16px; padding: 1rem 1.25rem;
  background: var(--surface); margin-bottom: 0.75rem;
}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--accent-soft); border-color: rgba(91, 140, 255, 0.35);
}
div[data-testid="stChatMessage"] p { line-height: 1.65; }

/* Chat input */
div[data-testid="stChatInput"] { border-radius: 16px; border: 1px solid var(--border); }
div[data-testid="stChatInput"]:focus-within { border-color: var(--accent); }
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)


# ── Backend hook (unchanged) ─────────────────────────────────────────────────
@st.cache_resource
def get_chain():
    return build_chain()


# ── Session state ────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


def ask(q: str):
    """Button callback: queue a question to be sent through the RAG chain."""
    st.session_state.pending_question = q


def new_chat():
    """Button callback: clear the current conversation."""
    st.session_state.messages = []
    st.session_state.pending_question = None


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div class="brand">
          <div class="brand-logo">📡</div>
          <div class="brand-name">Telecom Support</div>
        </div>
        <div class="brand-sub">Your AI-powered customer care assistant</div>
        """,
        unsafe_allow_html=True,
    )

    st.button("＋  New Chat", type="primary", on_click=new_chat, key="new_chat")

    st.markdown('<div class="side-label">Quick Help</div>', unsafe_allow_html=True)
    for i, (label, q) in enumerate(QUICK_HELP):
        st.button(label, on_click=ask, args=(q,), key=f"quick_{i}")

    st.markdown(
        '<div class="side-footer"><span class="dot"></span>Powered by RAG · GPT-OSS-120B</div>',
        unsafe_allow_html=True,
    )

# ── Resolve the question (chat input or button click) ───────────────────────
question = st.chat_input("Describe your issue...")
if st.session_state.pending_question:
    question = st.session_state.pending_question
    st.session_state.pending_question = None

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
      <div>
        <div class="hero-brand">Telecom Support</div>
        <h1>Customer Care Assistant</h1>
        <p>Ask about connectivity, billing, SIM, roaming, and more.</p>
      </div>
      <span class="pill"><span class="dot"></span>Online</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Welcome state ────────────────────────────────────────────────────────────
if not st.session_state.messages and not question:
    st.markdown(
        '<div class="welcome"><h2>How can we help today?</h2>'
        "<p>Pick a common question or describe your issue below.</p></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, q in enumerate(SAMPLE_QUESTIONS):
        with cols[i % 2]:
            st.button(q, on_click=ask, args=(q,), key=f"suggest_{i}")

# ── Conversation history ─────────────────────────────────────────────────────
AVATARS = {"user": "👤", "assistant": "📡"}

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=AVATARS.get(msg["role"])):
        st.markdown(msg["content"])

# ── New question → existing RAG pipeline ─────────────────────────────────────
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(question)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        chain = get_chain()
        status = st.empty()
        status.caption("● Searching the knowledge base…")

        def _stream():
            # Passes chunks through untouched; only clears the status line
            # once the first token arrives.
            first = True
            for chunk in chain.stream(question):
                if first:
                    status.empty()
                    first = False
                yield chunk

        response = st.write_stream(_stream())
        status.empty()

    st.session_state.messages.append({"role": "assistant", "content": response})