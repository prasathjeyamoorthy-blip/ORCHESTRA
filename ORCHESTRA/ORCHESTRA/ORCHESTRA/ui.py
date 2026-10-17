import streamlit as st
import requests
import uuid

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="ORCHESTRA – TNeGA AI",
    page_icon="🎼",
    layout="centered"
)

# ===============================
# SESSION STATE
# ===============================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "css_loaded" not in st.session_state:
    st.session_state.css_loaded = False

# ===============================
# CUSTOM CSS (Loaded once)
# ===============================
if not st.session_state.css_loaded:
    st.markdown("""
    <style>
    .stApp {
        background-color: #f7f7f8;
    }

    /* Gradient Header */
    .header {
        background: linear-gradient(90deg, #1d4ed8, #2563eb);
        padding: 14px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 18px;
    }

    .header h1 {
        font-size: 26px;
        margin: 0;
    }

    .header p {
        font-size: 14px;
        margin: 4px 0 0 0;
        opacity: 0.9;
    }

    /* Chat bubbles */
    [data-testid="stChatMessage"] {
        border-radius: 16px;
        padding: 12px;
        margin-bottom: 8px;
        max-width: 90%;
    }

    [data-testid="stChatMessage"][aria-label="user message"] {
        background-color: #e8f0fe;
        margin-left: auto;
    }

    [data-testid="stChatMessage"][aria-label="assistant message"] {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        margin-right: auto;
    }

    textarea {
        border-radius: 14px !important;
    }

    .footer {
        text-align: center;
        font-size: 13px;
        color: #9ca3af;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.session_state.css_loaded = True

# ===============================
# HEADER
# ===============================
st.markdown("""
<div class="header">
    <h1>🎼 ORCHESTRA – TNeGA AI Assistant</h1>
    <p>Official e-Sevai Residence Certificate Guidance</p>
</div>
""", unsafe_allow_html=True)

# ===============================
# SIDEBAR (INTERACTIVE)
# ===============================
with st.sidebar:
    st.markdown("### 🏛️ About")
    st.write(
        "This assistant helps citizens apply for a **Residence Certificate** "
        "through the TNeGA e-Sevai portal."
    )

    st.markdown("### 💡 You can ask")
    st.markdown("""
    - I want to apply for residence certificate  
    - What documents are required?  
    - What is the access type?  
    - What is the service charge?  
    """)

    st.markdown("---")

    if st.button("🔄 New Chat"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# ===============================
# CHAT HISTORY
# ===============================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===============================
# CHAT INPUT
# ===============================
user_input = st.chat_input("Ask about residence certificate, documents, fees…")

if user_input:
    # User message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    with st.chat_message("user"):
        st.markdown(user_input)

    # Assistant response
    with st.spinner("ORCHESTRA is thinking…"):
        try:
            response = requests.post(
                "http://localhost:8000/chat",
                json={
                    "session_id": st.session_state.session_id,
                    "message": user_input
                },
                timeout=30
            ).json()

            answer = response.get("answer", "Something went wrong.")

        except Exception:
            answer = "❌ Unable to connect to the server."

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
    with st.chat_message("assistant"):
        st.markdown(answer)

    st.rerun()

# ===============================
# FOOTER
# ===============================
st.markdown(
    '<div class="footer">Powered by TNeGA • ORCHESTRA AI</div>',
    unsafe_allow_html=True
)
