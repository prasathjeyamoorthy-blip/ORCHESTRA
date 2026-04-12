# generation/chain.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from retrieval.retriever import HybridRetriever
from generation.llm import generate_answer
from memory.memory_manager import MemoryManager
from intent.intent_detector import detect_intent, Intent
from intent.followup_suggester import get_followup_suggestions
from intent.language_detector import detect_language
from agent.receptionist import handle_message


GREETING_RESPONSES = {
    "en": "Hey there! 👋 I'm your PAN card assistant. I can help you with PAN applications, documents, Aadhaar linking, e-PAN downloads, and more. What would you like to know?",
    "ta": "வணக்கம்! 👋 நான் உங்கள் PAN கார்டு உதவியாளர். PAN விண்ணப்பம், ஆவணங்கள், ஆதார் இணைப்பு மற்றும் மேலும் உதவ தயாராக இருக்கிறேன்!",
    "hi": "नमस्ते! 👋 मैं आपका PAN कार्ड सहायक हूँ। PAN आवेदन, दस्तावेज़, आधार लिंकिंग और अधिक में मदद के लिए तैयार हूँ!",
}

FAREWELL_RESPONSES = {
    "en": "Goodbye! 😊 Feel free to come back anytime you have PAN related questions. Have a great day!",
    "ta": "நன்றி! 😊 எந்த நேரத்திலும் திரும்பி வாருங்கள். நல்ல நாள்!",
    "hi": "अलविदा! 😊 कभी भी PAN संबंधित प्रश्नों के साथ वापस आएं। आपका दिन शुभ हो!",
}

GRATITUDE_RESPONSES = {
    "en": "You're welcome! 😊 Let me know if you have more questions about PAN services.",
    "ta": "மகிழ்ச்சி! 😊 PAN சேவைகள் பற்றி மேலும் கேள்விகள் இருந்தால் கேளுங்கள்.",
    "hi": "आपका स्वागत है! 😊 PAN सेवाओं के बारे में और प्रश्न हों तो पूछें।",
}

UNRELATED_RESPONSES = {
    "en": (
        "Hmm, that's outside my area of expertise! 😅 "
        "I'm specifically here to help with PAN card services.\n\n"
        "Here's what I can help you with:\n"
        "• PAN card application (new / correction / reprint)\n"
        "• Required documents for PAN\n"
        "• Aadhaar-PAN linking\n"
        "• e-PAN download\n"
        "• TAN and TDS queries\n"
        "• PAN application status tracking\n\n"
        "Feel free to ask me anything from the above! 😊"
    ),
    "ta": (
        "அந்த விஷயம் என் திறன் வரம்பிற்கு வெளியே! 😅 "
        "நான் PAN கார்டு சேவைகளுக்கு மட்டுமே உதவ முடியும்.\n\n"
        "நான் உதவக்கூடியவை:\n"
        "• PAN விண்ணப்பம்\n"
        "• தேவையான ஆவணங்கள்\n"
        "• ஆதார்-PAN இணைப்பு\n"
        "• e-PAN பதிவிறக்கம்"
    ),
    "hi": (
        "यह मेरी विशेषज्ञता से बाहर है! 😅 "
        "मैं केवल PAN कार्ड सेवाओं में मदद कर सकता हूँ।\n\n"
        "मैं इनमें मदद कर सकता हूँ:\n"
        "• PAN कार्ड आवेदन\n"
        "• आवश्यक दस्तावेज़\n"
        "• आधार-PAN लिंकिंग\n"
        "• e-PAN डाउनलोड"
    ),
}

ROLEPLAY_RESPONSES = {
    "en": "I appreciate the creativity, but I'm strictly a PAN card assistant! 😊 I can't take on a different role. Let me know if you have any PAN related questions!",
    "ta": "நான் PAN கார்டு உதவியாளர் மட்டுமே! 😊 வேறு பாத்திரம் எடுக்க முடியாது.",
    "hi": "मैं सिर्फ PAN कार्ड सहायक हूँ! 😊 कोई अलग भूमिका नहीं ले सकता।",
}

IDENTITY_RESPONSES = {
    "en": (
        "Hey! I'm the Protean PAN Assistant 😊\n\n"
        "I'm here to make PAN card services easy for you! Here's what I can help with:\n"
        "• New PAN card application\n"
        "• Document requirements\n"
        "• Aadhaar-PAN linking\n"
        "• e-PAN download\n"
        "• PAN correction or reprint\n"
        "• TAN and TDS queries\n\n"
        "Just ask me anything! 🎯"
    ),
    "ta": "நான் Protean PAN உதவியாளர்! 😊 PAN சேவைகளை எளிதாக்க இங்கே இருக்கிறேன்.",
    "hi": "मैं Protean PAN सहायक हूँ! 😊 PAN सेवाओं को आसान बनाने के लिए यहाँ हूँ।",
}

JUNK_RESPONSES = {
    "en": "Hmm, I didn't quite catch that! 😅 Could you rephrase your question? I'm here to help with PAN card queries.",
    "ta": "புரியவில்லை! 😅 மீண்டும் கேளுங்கள்.",
    "hi": "समझ नहीं आया! 😅 कृपया दोबारा पूछें।",
}

ABUSE_RESPONSES = {
    "en": "Let's keep things friendly! 😊 I'm here to help you with PAN card queries. What would you like to know?",
    "ta": "நட்புடன் பேசுவோம்! 😊 PAN கேள்விகளுக்கு உதவ தயாராக இருக்கிறேன்.",
    "hi": "दोस्ताना बातचीत करें! 😊 PAN सेवाओं में मदद के लिए यहाँ हूँ।",
}

STATIC_RESPONSES = {
    Intent.GREETING:  GREETING_RESPONSES,
    Intent.FAREWELL:  FAREWELL_RESPONSES,
    Intent.GRATITUDE: GRATITUDE_RESPONSES,
    Intent.UNRELATED: UNRELATED_RESPONSES,
    Intent.ROLEPLAY:  ROLEPLAY_RESPONSES,
    Intent.IDENTITY:  IDENTITY_RESPONSES,
    Intent.JUNK:      JUNK_RESPONSES,
    Intent.ABUSE:     ABUSE_RESPONSES,
}


class RAGChain:

    def __init__(self):
        print("Initialising RAG chain...")
        self.retriever = HybridRetriever()
        self.memory = MemoryManager()
        print("✅ RAG chain ready\n")

    def run(self, question: str, session_id: str = None, user_id: str = "anonymous") -> dict:

        if not session_id:
            session_id = MemoryManager.new_session_id()

        language = detect_language(question)
        intent   = detect_intent(question)
        print(f"DEBUG intent: {intent.value} | language: {language}")

        # ── If there's an active guided flow, bypass intent checks ────
        # User is mid-flow (e.g. typed "1" to select applicant type)
        from agent.flow_manager import FlowManager
        if FlowManager(session_id).has_active_flow():
            agent_response = handle_message(question, session_id, language)
            if agent_response:
                return {
                    "question"  : question,
                    "answer"    : agent_response["answer"],
                    "sources"   : [],
                    "session_id": session_id,
                    "intent"    : intent.value,
                    "language"  : language,
                    "followups" : agent_response.get("followups", []),
                }

        # ── Safety gate: block roleplay/abuse/junk BEFORE anything else ──
        BLOCKED_INTENTS = {
            Intent.ROLEPLAY, Intent.ABUSE, Intent.JUNK,
            Intent.UNRELATED, Intent.GREETING, Intent.FAREWELL,
            Intent.GRATITUDE, Intent.IDENTITY,
        }
        if intent in BLOCKED_INTENTS:
            responses = STATIC_RESPONSES[intent]
            answer    = responses.get(language, responses["en"])
            return {
                "question"  : question,
                "answer"    : answer,
                "sources"   : [],
                "session_id": session_id,
                "intent"    : intent.value,
                "language"  : language,
                "followups" : [],
            }

        # ── Agent: handles active flows + service detection ───────────
        agent_response = handle_message(question, session_id, language)
        if agent_response:
            return {
                "question"  : question,
                "answer"    : agent_response["answer"],
                "sources"   : [],
                "session_id": session_id,
                "intent"    : intent.value,
                "language"  : language,
                "followups" : agent_response.get("followups", []),
            }

        # ── Remaining static intents (shouldn't reach here, safety net) ──
        if intent in STATIC_RESPONSES:
            responses = STATIC_RESPONSES[intent]
            answer    = responses.get(language, responses["en"])
            return {
                "question"  : question,
                "answer"    : answer,
                "sources"   : [],
                "session_id": session_id,
                "intent"    : intent.value,
                "language"  : language,
                "followups" : [],
            }

        # ── RAG pipeline ──────────────────────────────────────────────
        session_history = self.memory.get_session_history(session_id)
        history_text    = ""
        if session_history:
            history_text = "\n".join(
                [f"User: {h['query']}\nBot: {h['answer']}" for h in session_history[-5:]]
            )

        chunks    = self.retriever.retrieve(question)
        answer    = generate_answer(question, chunks, history_text=history_text, language=language)
        followups = get_followup_suggestions(question, answer)

        self.memory.add_to_session(session_id, question, answer)
        self.memory.update_user_memory(user_id, question, answer)

        seen           = set()
        unique_sources = []
        for c in chunks:
            if c["url"] not in seen:
                seen.add(c["url"])
                unique_sources.append({"title": c["title"], "url": c["url"]})

        return {
            "question"  : question,
            "answer"    : answer,
            "sources"   : unique_sources,
            "session_id": session_id,
            "intent"    : intent.value,
            "language"  : language,
            "followups" : followups,
        }