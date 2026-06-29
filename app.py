import glob
import requests
import streamlit as st
from PyPDF2 import PdfReader

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
        --navy: #17233F;
        --blue: #245EAE;
        --teal: #169FB5;
        --gold: #D6A63A;
        --pale: #F4FAFC;
    }
    .stApp {
        background: linear-gradient(180deg, #F8FCFD 0%, #FFFFFF 50%, #F8FCFD 100%);
    }
    .block-container {
        padding-top: 2.3rem;
        max-width: 980px;
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 850;
        color: var(--navy);
        margin-bottom: 0.1rem;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        color: #3F7894;
        font-size: 1.18rem;
        font-weight: 650;
        margin-bottom: 0.8rem;
    }
    .gold-line {
        height: 4px;
        background: linear-gradient(90deg, var(--gold), #F1D27A, var(--teal));
        border-radius: 999px;
        margin: 0.5rem 0 1.5rem 0;
    }
    .welcome-card {
        background: linear-gradient(135deg, #F1FAFC 0%, #FFFFFF 100%);
        border: 1px solid #BEE0E7;
        border-left: 7px solid var(--gold);
        border-radius: 18px;
        padding: 1.3rem 1.45rem;
        box-shadow: 0 8px 24px rgba(23, 35, 63, 0.06);
        color: #374151;
        font-size: 1.02rem;
        line-height: 1.72;
    }
    .note-card {
        background: #FFF8E8;
        border: 1px solid #EAC76A;
        border-radius: 14px;
        padding: 0.9rem 1.1rem;
        color: #4B5563;
        font-size: 0.95rem;
        line-height: 1.55;
        margin-top: 1rem;
    }
    .section-label {
        font-size: 1.18rem;
        font-weight: 800;
        color: var(--navy);
        margin-top: 1.6rem;
        margin-bottom: 0.7rem;
    }
    div.stButton > button {
        border: 1px solid #BEE0E7;
        background: #FFFFFF;
        color: #17324D;
        border-radius: 999px;
        padding: 0.55rem 0.9rem;
        font-weight: 600;
        min-height: 2.55rem;
    }
    div.stButton > button:hover {
        border-color: var(--gold);
        color: var(--navy);
        background: #FFF9E9;
    }
    .footer {
        color: #6B7280;
        font-size: 0.9rem;
        line-height: 1.6;
        margin-top: 1.4rem;
    }
    .footer em {
        color: #4B5563;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Header
# -----------------------------
st.markdown('<div class="hero-title">Ask the Abstract</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">AI-powered study companion</div>', unsafe_allow_html=True)
st.markdown('<div class="gold-line"></div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="welcome-card">
    <strong>Welcome!</strong> This AI-powered study companion has been developed from the content of our AMEE 2026 study to help you explore the research in greater depth.<br><br>
    You can ask about the study background, methodology, findings, qualitative themes, recommendations, or practical implications for examiner training and assessment practice.<br><br>
    Responses are generated exclusively from the uploaded study material.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="note-card">
    <strong>Note:</strong> This assistant supports exploration of the uploaded study material. It is not intended to replace reading the abstract, poster, or accompanying resources.
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# API key
# -----------------------------
try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    st.error("OpenRouter API key is missing. Add OPENROUTER_API_KEY in Streamlit Secrets.")
    st.stop()

# -----------------------------
# Load PDF text
# -----------------------------
@st.cache_data(show_spinner=False)
def load_pdf_text() -> str:
    pdf_files = glob.glob("*.pdf")
    if not pdf_files:
        return ""
    text_parts = []
    for pdf_file in pdf_files:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts).strip()

study_text = load_pdf_text()

if not study_text:
    st.error("No readable PDF was found in the app repository.")
    st.stop()

SYSTEM_INSTRUCTION = f"""
You are an AI-powered study companion for an AMEE 2026 Learning Toolbox.

You must answer only from the uploaded study material provided below.
Do not invent facts, figures, authors, findings, themes, recommendations, limitations, or implications.
If the uploaded study material does not contain enough information to answer a question, say exactly:
"The uploaded study material does not provide this information."

Write clearly and concisely for medical educators, examiners, and health professions faculty.
Use British English.
Avoid overclaiming causality. Do not say the study proves impact; say it reports or suggests sustained change where appropriate.
When helpful, structure responses in short paragraphs or concise bullet points.
Do not mention the name of the model or the API provider.

UPLOADED STUDY MATERIAL:
{study_text}
"""

# A free OpenRouter model. If unavailable, change this to another free model from OpenRouter.
OPENROUTER_MODEL = "openrouter/free"

# -----------------------------
# Session state
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------
# Utility function
# -----------------------------
def ask_openrouter(user_question: str) -> str:
    conversation = []
    for msg in st.session_state.messages[-8:]:
        conversation.append({"role": msg["role"], "content": msg["content"]})
    conversation.append({"role": "user", "content": user_question})

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            *conversation,
        ],
        "temperature": 0.2,
        "max_tokens": 750,
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://streamlit.app",
            "X-Title": "Ask the Abstract",
        },
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        return f"The assistant could not generate a response at this moment. Error {response.status_code}: {response.text}"

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return "The assistant could not generate a response at this moment. Please try again."

# -----------------------------
# Controls and suggested questions
# -----------------------------
col_a, col_b = st.columns([1, 3])
with col_a:
    if st.button("Start a new conversation"):
        st.session_state.messages = []
        st.rerun()
with col_b:
    st.markdown("<div style='color:#6B7280; padding-top:0.55rem;'>Ask a question or choose one of the prompts below.</div>", unsafe_allow_html=True)

st.markdown('<div class="section-label">Suggested questions</div>', unsafe_allow_html=True)

suggested_questions = [
    "Why was this study undertaken?",
    "How was the mixed-methods study conducted?",
    "What were the main quantitative findings?",
    "What qualitative themes emerged?",
    "What barriers affected sustained examiner practice?",
    "What recommendations did the authors make?",
    "What is the main take-home message?",
    "What are the practical implications for examiner development?",
]

selected_question = None
cols = st.columns(2)
for i, question in enumerate(suggested_questions):
    with cols[i % 2]:
        if st.button(question, key=f"suggested_{i}"):
            selected_question = question

# -----------------------------
# Existing chat messages
# -----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_question = st.chat_input("Ask a question about the study...")
if selected_question:
    user_question = selected_question

if user_question:
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        with st.spinner("Reviewing the uploaded study material..."):
            answer = ask_openrouter(user_question)
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
