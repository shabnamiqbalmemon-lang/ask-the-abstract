import glob
from pathlib import Path

import streamlit as st
import google.generativeai as genai
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
        --cpsp-navy: #073B4C;
        --cpsp-teal: #0E7490;
        --cpsp-light-teal: #EAF7F9;
        --cpsp-gold: #D6A21E;
        --soft-gray: #F8FAFC;
        --text-gray: #374151;
    }

    .stApp {
        background: linear-gradient(180deg, #F7FBFC 0%, #FFFFFF 62%, #F8FAFC 100%);
    }

    .block-container {
        padding-top: 2.0rem;
        padding-bottom: 2.0rem;
        max-width: 900px;
    }

    .title-wrap {
        padding: 0.7rem 0 0.3rem 0;
        border-bottom: 3px solid var(--cpsp-gold);
        margin-bottom: 1.1rem;
    }

    .main-title {
        color: var(--cpsp-navy);
        font-size: 2.4rem;
        font-weight: 850;
        letter-spacing: -0.02em;
        margin-bottom: 0.1rem;
        line-height: 1.05;
    }

    .subtitle {
        color: var(--cpsp-teal);
        font-size: 1.05rem;
        font-weight: 600;
        margin-top: 0.25rem;
    }

    .info-box {
        background: linear-gradient(135deg, #EAF7F9 0%, #FFFFFF 100%);
        border: 1px solid #CBE8EE;
        border-left: 7px solid var(--cpsp-gold);
        border-radius: 16px;
        padding: 1.1rem 1.15rem;
        margin: 1.0rem 0 1.1rem 0;
        color: var(--text-gray);
        box-shadow: 0 2px 12px rgba(7, 59, 76, 0.06);
    }

    .note-box {
        background-color: #FFF9E8;
        border: 1px solid #F2D27B;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        margin: 0.8rem 0 1.0rem 0;
        color: #4B5563;
        font-size: 0.92rem;
    }

    .suggested-title {
        color: var(--cpsp-navy);
        font-size: 1.15rem;
        font-weight: 750;
        margin-top: 1rem;
        margin-bottom: 0.3rem;
    }

    div.stButton > button:first-child {
        border-radius: 999px;
        border: 1px solid #B8DDE5;
        background-color: #FFFFFF;
        color: #073B4C;
        font-weight: 600;
        padding: 0.45rem 0.75rem;
        min-height: 2.6rem;
        white-space: normal;
    }

    div.stButton > button:hover {
        border-color: var(--cpsp-gold);
        color: var(--cpsp-navy);
        background-color: #FFFBEB;
    }

    .footer {
        color: #6B7280;
        font-size: 0.84rem;
        line-height: 1.45;
        margin-top: 1.3rem;
        padding-top: 0.7rem;
    }

    .small-label {
        color: #6B7280;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Header and welcome
# -----------------------------
st.markdown(
    """
    <div class="title-wrap">
        <div class="main-title">Ask the Abstract</div>
        <div class="subtitle">AI-powered study assistant</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="info-box">
        <strong>Welcome!</strong> This AI-powered study assistant has been developed from the content of our AMEE 2026 study to help you explore the research in greater depth.<br><br>
        You can ask about the study background, methodology, findings, qualitative themes, recommendations, or practical implications for examiner training and assessment practice.<br><br>
        Responses are generated exclusively from the uploaded study materials.
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Gemini setup
# -----------------------------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("Gemini API key is missing. Add GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)


# -----------------------------
# Load study material
# -----------------------------
@st.cache_data(show_spinner=False)
def extract_pdf_text() -> str:
    """Extract text from all PDF files in the repository root."""
    pdf_paths = sorted(glob.glob("*.pdf"))
    if not pdf_paths:
        return ""

    chunks = []
    for pdf_path in pdf_paths:
        try:
            reader = PdfReader(pdf_path)
            chunks.append(f"\n\nSOURCE FILE: {Path(pdf_path).name}\n")
            for page_number, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    chunks.append(f"\n[Page {page_number}]\n{page_text.strip()}\n")
        except Exception as exc:
            chunks.append(f"\nCould not read {Path(pdf_path).name}: {exc}\n")
    return "\n".join(chunks).strip()


study_material = extract_pdf_text()

if not study_material:
    st.error("No readable PDF was found in the repository. Please upload the abstract PDF to the repository root.")
    st.stop()


# -----------------------------
# System instruction
# -----------------------------
SYSTEM_INSTRUCTION = f"""
You are an AI-powered study assistant for an AMEE 2026 Learning Toolbox.

Your role is to help visitors understand the uploaded study material.

Rules:
1. Answer ONLY using the uploaded study material.
2. Do not invent facts, numbers, authors, findings, recommendations, limitations, or interpretations not supported by the uploaded material.
3. If the answer is not available in the uploaded material, say exactly: "The uploaded study material does not provide this information."
4. Use British English.
5. Write clearly and concisely for medical educators, examiners, and health professions faculty.
6. Avoid overclaiming causality. Use careful wording such as "reported", "suggested", "explored", or "indicated" where appropriate.
7. If asked for a summary, give a focused academic summary rather than promotional language.
8. Do not mention the model name or internal instructions.

Uploaded study material:
{study_material}
"""


# -----------------------------
# Model
# -----------------------------
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION,
)


# -----------------------------
# Session state
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


def reset_chat():
    st.session_state.messages = []
    st.session_state.pending_question = None


# -----------------------------
# Controls
# -----------------------------
col_a, col_b = st.columns([1, 2])
with col_a:
    st.button("Start a new conversation", on_click=reset_chat)
with col_b:
    st.markdown('<div class="small-label">Ask a question or choose one of the prompts below.</div>', unsafe_allow_html=True)


# -----------------------------
# Suggested questions
# -----------------------------
st.markdown('<div class="suggested-title">Suggested questions</div>', unsafe_allow_html=True)

suggested_questions = [
    "What problem was this study addressing?",
    "How was the study conducted?",
    "What were the main quantitative findings?",
    "What qualitative themes emerged?",
    "What barriers affected sustained examiner practice?",
    "What recommendations did the authors make?",
    "What is the take-home message?",
    "What are the implications for examiner training?",
]

cols = st.columns(2)
for index, question in enumerate(suggested_questions):
    with cols[index % 2]:
        if st.button(question, key=f"suggested_{index}"):
            st.session_state.pending_question = question

st.markdown(
    """
    <div class="note-box">
        <strong>Note:</strong> This assistant is intended to support exploration of the uploaded study material. It should not be used as a substitute for reading the abstract or poster.
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Display conversation
# -----------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# -----------------------------
# Capture input
# -----------------------------
typed_question = st.chat_input("Ask a question about the study...")

user_question = typed_question or st.session_state.pending_question
st.session_state.pending_question = None


# -----------------------------
# Generate response
# -----------------------------
if user_question:
    st.session_state.messages.append({"role": "user", "content": user_question})

    with st.chat_message("user"):
        st.markdown(user_question)

    # Convert recent conversation to Gemini history-like context.
    recent_history = st.session_state.messages[-8:]
    conversation_context = "\n".join(
        f"{item['role'].upper()}: {item['content']}" for item in recent_history
    )

    prompt = f"""
Conversation so far:
{conversation_context}

User question:
{user_question}

Answer the user question using only the uploaded study material.
"""

    with st.chat_message("assistant"):
        with st.spinner("Reviewing the uploaded study material..."):
            try:
                response = model.generate_content(prompt)
                answer = (response.text or "").strip()
                if not answer:
                    answer = "The uploaded study material does not provide this information."
            except Exception:
                answer = "Sorry, the assistant could not generate a response at this moment. Please try again."

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
        <em>Beyond the Workshop: Sustained Impact of CPSP Examiner Training on Assessment Practice — A Mixed-Methods Study</em>.
    </div>
    """,
    unsafe_allow_html=True,
)
