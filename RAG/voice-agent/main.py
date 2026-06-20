"""
Voice RAG Agent — main entry point
Run: python main.py
"""

from core.agent import VoiceAgent

if __name__ == "__main__":
    agent = VoiceAgent()
    agent.run()