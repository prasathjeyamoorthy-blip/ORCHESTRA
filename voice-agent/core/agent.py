"""
core/agent.py — Voice Agent Orchestrator
Wires STT → RAG → LLM → TTS with conversational intelligence.
Detects user emotion/intent to vary tone and acknowledgment.
"""

import re
from core.stt      import SpeechToText
from core.tts      import TextToSpeech
from core.llm      import OllamaLLM
from rag.retriever import RAGRetriever
from core.voice_receptionist import VoiceReceptionist


EXIT_WORDS  = {"exit", "quit", "stop", "goodbye", "bye", "shut down"}
RESET_WORDS = {"reset", "start over", "clear", "new conversation"}

# ── Conversational openers — rotated to avoid repetition ─────────────────────
_GREETINGS = [
    "Hello! Great to have you here.",
    "Hey there! I'm your PAN card assistant.",
    "Hi! Ready to help you with anything PAN related.",
    "Hello! What can I sort out for you today?",
]

# ── Emotion / intent signals for adaptive responses ───────────────────────────
_CONFUSED = re.compile(
    r"\b(confused|don.?t understand|not sure|what do you mean|unclear|"
    r"lost|complicated|difficult|hard to|can you explain|huh|what)\b",
    re.IGNORECASE
)
_URGENT = re.compile(
    r"\b(urgent|asap|immediately|deadline|today|right now|quickly|fast|"
    r"hurry|emergency|last date|expire|penalty)\b",
    re.IGNORECASE
)
_FRUSTRATED = re.compile(
    r"\b(not working|doesn.?t work|failed|rejected|wrong|error|problem|"
    r"issue|stuck|can.?t|unable|still not|again|why is|why does)\b",
    re.IGNORECASE
)
_GRATEFUL = re.compile(
    r"\b(thank|thanks|helpful|great|perfect|awesome|excellent|got it|"
    r"understood|clear now|makes sense)\b",
    re.IGNORECASE
)


def _detect_emotion(text: str) -> str:
    """Returns an emotion tag to guide the LLM's tone."""
    if _FRUSTRATED.search(text): return "frustrated"
    if _URGENT.search(text):     return "urgent"
    if _CONFUSED.search(text):   return "confused"
    if _GRATEFUL.search(text):   return "grateful"
    return "neutral"


def _build_context_hint(emotion: str, user_text: str) -> str:
    """
    Prepends a tone instruction to the user message so the LLM
    adapts its response style without changing the system prompt.
    """
    hints = {
        "frustrated": "[User seems frustrated. Acknowledge their difficulty first, then help calmly and clearly.] ",
        "urgent":     "[User has an urgent need. Be direct and prioritize the most important information first.] ",
        "confused":   "[User seems confused. Start with a simple reassurance, then explain step by step.] ",
        "grateful":   "[User is expressing thanks. Respond warmly and briefly, then offer to help further.] ",
        "neutral":    "",
    }
    return hints.get(emotion, "") + user_text


class VoiceAgent:

    def __init__(self, user_id: str = "voice_user"):
        print("\n🚀 Starting Voice RAG Agent...\n")
        self.stt        = SpeechToText()
        self.tts        = TextToSpeech()
        self.llm        = OllamaLLM()
        self.retriever  = RAGRetriever()
        self.receptionist = VoiceReceptionist()
        self._turn      = 0          # tracks conversation turns for varied responses
        self._last_open = ""         # tracks last opener to avoid repetition
        self._history   = []         # per-agent conversation history (CLI mode only)
        self._session_id = f"voice_{user_id}_{int(__import__('time').time())}"
        self._user_id    = user_id
        print("\n✅ All systems ready!\n")

    def _should_exit(self, text: str) -> bool:
        return any(w in text.lower() for w in EXIT_WORDS)

    def _should_reset(self, text: str) -> bool:
        return any(w in text.lower() for w in RESET_WORDS)

    def _process_and_speak(self, user_text: str) -> str:
        """
        Full pipeline:
        1. Check if this is a PAN registration flow query
        2. If yes, use voice receptionist for guided flow
        3. If no, use standard RAG + LLM pipeline
        4. Speak the response sentence by sentence
        """
        # Try PAN registration flow first
        guided_response = self.receptionist.process_voice_query(
            user_text=user_text,
            session_id=self._session_id,
            user_id=self._user_id,
            conversation_history=self._history
        )

        if guided_response and guided_response.get("guided"):
            # Guided flow response — speak it directly
            reply = guided_response["text"]
            print(f"🎯 Guided Flow: {guided_response.get('step', 'unknown')}")
            print(f"🤖 Agent: {reply}")
            
            # Speak the response
            self._speak_text(reply)
            
            # Update history
            self._history.append({"role": "user", "content": user_text})
            self._history.append({"role": "assistant", "content": reply})
            if len(self._history) > 20:
                self._history = self._history[-20:]
            self._turn += 1
            return reply

        # Not a guided flow — use standard RAG + LLM
        emotion = _detect_emotion(user_text)
        augmented_text = _build_context_hint(emotion, user_text)

        context = self.retriever.get_context(user_text)
        if context:
            print(f"📄 RAG context ({len(context)} chars) | emotion: {emotion}")
        else:
            print(f"📄 No RAG context | emotion: {emotion}")

        full_reply = ""
        first = True
        for sentence in self.llm.stream(augmented_text, context=context, history=self._history):
            if first:
                print(f"🤖 Agent: ", end="", flush=True)
                first = False
            print(sentence, end=" ", flush=True)
            full_reply += sentence + " "
            self.tts.speak(sentence)

        print()
        # Update per-agent history
        self._history.append({"role": "user", "content": augmented_text})
        self._history.append({"role": "assistant", "content": full_reply.strip()})
        if len(self._history) > 20:
            self._history = self._history[-20:]
        self._turn += 1
        return full_reply.strip()

    def _speak_text(self, text: str):
        """Break text into sentences and speak each one."""
        import re
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            if sentence.strip():
                self.tts.speak(sentence.strip())

    def run(self):
        print("=" * 55)
        print("  🎙️  Voice RAG Agent is running")
        print("  Say 'exit' or 'quit' to stop")
        print("  Say 'reset' to start a new conversation")
        print("=" * 55)

        # Varied opening greeting
        import random
        opening = random.choice(_GREETINGS) + " How can I help you today?"
        self.tts.speak(opening)

        while True:
            try:
                user_text = self.stt.listen()

                if not user_text or len(user_text.strip()) < 2:
                    # After a few missed turns, prompt gently
                    if self._turn > 0:
                        self.tts.speak("I didn't catch that — go ahead whenever you're ready.")
                    continue

                print(f"\n👤 You: {user_text}")

                if self._should_exit(user_text):
                    self.tts.speak("It was great talking with you! Come back anytime you need PAN help. Goodbye!")
                    print("\n👋 Session ended")
                    break

                if self._should_reset(user_text):
                    self._history = []
                    self._turn = 0
                    self.tts.speak("Sure, let's start fresh. What would you like to know?")
                    continue

                self._process_and_speak(user_text)

            except KeyboardInterrupt:
                print("\n\n⛔ Interrupted by user")
                self.tts.speak("Alright, shutting down. Take care!")
                break

            except Exception as e:
                print(f"\n❌ Error: {e}")
                self.tts.speak("Hmm, something went wrong on my end. Could you try that again?")
                continue
