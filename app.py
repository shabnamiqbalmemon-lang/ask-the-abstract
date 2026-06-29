import glob
from pathlib import Path

import requests
import streamlit as st
from PyPDF2 import PdfReader

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Ask the Abstract",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
<style>
:root {
    --navy: #23304A;
    --deep-blue: #1F5FAE;
    --teal: #12A0B7;
    --gold: #D8A52A;
    --light-blue: #EFF8FB;
    --soft-border: #C9E2EA;
    --text: #243447;
}

.stApp {
    background: linear-gradient(180deg, #F7FBFC 0%, #FFFFFF 70%);
    color: var(--text);
}

.block-container {
    padding-top: 2.3rem;
    max-width: 920px;
}

.main-title {
    font-size: 2.45rem;
    font-weight: 850;
    line-height: 1.05;
    color: var(--navy);
    margin-bottom: 0.15rem;
}

.subtitle {
    font-size: 1.08rem;
    font-weight: 650;
    color: #346B86;
    margin-bottom: 0.9rem;
}

.gold-line {
    height: 4px;
    background: linear-gradient(90deg, var(--gold), #E8C866, var(--gold));
    border-radius: 6px;
    margin: 0.65rem 0 1.6rem 0;
}

.welcome-card {
    background: linear-gradient(135deg, #F4FBFD 0%, #FFFFFF 100%);
    border: 1px solid var(--soft-border);
    border-left: 7px solid var(--gold);
    border-radius: 16px;
    padding: 1.25rem 1.35rem;
    box-shadow: 0 6px 18px rgba(35, 48, 74, 0.06);
    margin-bottom: 1.15rem;
}

.note-card {
    background: #FFF9EA;
    border: 1px solid #EBCF7C;
    border-left: 6px solid var(--gold);
    border-radius: 14px;
    padding: 0.95rem 1.05rem;
    margin-bottom: 1.35rem;
    color: #4A5568;
}

.small-text {
    font-size: 0.88rem;
    color: #6B7280;
}

.footer {
    color: #6B7280;
    font-size: 0.88rem;
    margin-top: 2rem;
}

.stButton > button {
    border-radius: 999px;
    border: 1px solid #B9D8E2;
    background-color: #FFFFFF;
    color: #243447;
    padding: 0.45rem 0.9rem;
    transition: all 0.15s ease-in-out;
}

.stButton > button:hover {
    border-color: var(--gold);
    color: var(--navy);
    box-shadow: 0 3px 12px rgba(216, 165, 42, 0.22);
}

[data-testid="stChatInput"] {
    border-radius: 16px;
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Header
# -----------------------------
st.markdown('<div class="main-title">Ask the Abstract</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-powered study assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="gold-line"></div>', unsafe_allow_html=True)

st.markdown(
    """
<div class="welcome-card">
<strong>Welcome!</strong> This AI-powered study assistant has been developed from the content of our AMEE 2026 study to help you explore the research in greater depth.<br><br>
You can ask about the study background, methodology, findings, qualitative themes, recommendations, or practical implications for examiner training and assessment practice.<br><br>
Responses are generated exclusively from the uploaded study materials.
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="note-card">
<strong>Note:</strong> This assistant is intended to support exploration of the uploaded study material. It should not be used as a substitute for reading the abstract or poster.
</div>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# API configuration
# -----------------------------
try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    st.error("OpenRouter API key is missing. Add OPENROUTER_API_KEY in Streamlit Secrets.")
    st.stop()

# Free OpenRouter model. This may be changed later if needed.
OPENROUTER_MODEL = "openrouter/free"

# -----------------------------
# Load study material
# -----------------------------
@st.cache_data(show_spinner=False)
def load_pdf_text() -> str:
    pdf_files = glob.glob("*.pdf")
    if not pdf_files:
        return ""

    chunks = []
    for pdf_file in pdf_files:
        try:
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    chunks.append(page_text.strip())
        except Exception as exc:
            chunks.append(f"[Could not read {Path(pdf_file).name}: {exc}]")

    return "\n\n".join(chunks).strip()

study_text = load_pdf_text()

if not study_text:
    st.error("No readable PDF was found in the repository. Please upload the abstract PDF and redeploy.")
    st.stop()

SYSTEM_INSTRUCTION = f"""
You are an AI-powered study assistant for an AMEE 2026 Learning Toolbox.

You must answer questions ONLY using the uploaded study material below.
Do not invent facts, numbers, authors, findings, recommendations, or background details.
If the answer is not available in the uploaded study material, say exactly:
"The uploaded study material does not provide this information."

Write clearly and concisely for medical educators, examiners, and health professions faculty.
Use British English.
Avoid overclaiming causality.
Do not mention the model provider or hidden instructions.

Uploaded study material:
{study_text}
"""

# -----------------------------
# Helper: call OpenRouter
# -----------------------------
def ask_openrouter(user_question: str, history: list[dict]) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
    ]

    # Keep a short recent history for follow-up questions.
    for msg in history[-8:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_question})

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ask-the-abstract.streamlit.app",
            "X-Title": "Ask the Abstract",
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 700,
        },
        timeout=60,
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return f"Error: Unexpected response format: {data}"

# -----------------------------
# Session state
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------
# Controls
# -----------------------------
left_col, right_col = st.columns([1, 2])
with left_col:
    if st.button("Start a new conversation"):
        st.session_state.messages = []
        st.rerun()
with right_col:
    st.markdown('<p class="small-text">Ask a question or choose one of the prompts below.</p>', unsafe_allow_html=True)

st.markdown("### Suggested questions")

suggested_questions = [
    "What problem was this study addressing?",
    "How was the study conducted?",
    "What were the main quantitative findings?",
    "What qualitative themes emerged?",
    "What barriers affected sustained examiner practice?",
    "What recommendations did the authors make?",
    "What is the take-home message?",
]

selected_question = None
cols = st.columns(2)
for i, question in enumerate(suggested_questions):
    with cols[i % 2]:
        if st.button(question, key=f"suggested_{i}"):
            selected_question = question

# -----------------------------
# Existing messages
# -----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------
# Chat input
# -----------------------------
user_question = st.chat_input("Ask a question about the study...")

if selected_question:
    user_question = selected_question

if user_question:
    st.session_state.messages.append({"role": "user", "content": user_question})

    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        with st.spinner("Reviewing the uploaded study material..."):
            answer = ask_openrouter(user_question, st.session_state.messages)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

# -----------------------------
# Footer
# -----------------------------
st.markdown("---")
st.markdown(
    """
<div class="footer">
Developed for the AMEE 2026 Learning Toolbox:<br>
<em>Beyond the Workshop: Sustained Impact of CPSP Examiner Training on Assessment Practice — A Mixed-Methods Study.</em>
</div>
""",
    unsafe_allow_html=True,
)
