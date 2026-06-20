#!/usr/bin/env python3
"""Test Tamil translation after installing deep-translator"""

from agent.translator import translate_response

tests = [
    "Would you like to answer optional questions first?",
    "What is your full name?",
    "Please confirm your details",
    "Which of these fits you?",
    "How do you want to submit your PAN application documents?",
]

print("ENGLISH → TAMIL TRANSLATION TEST:")
print("=" * 70)

for english_text in tests:
    tamil_text = translate_response(english_text, "ta")
    print(f"\nEnglish: {english_text}")
    print(f"Tamil:   {tamil_text}")
    print("-" * 70)
