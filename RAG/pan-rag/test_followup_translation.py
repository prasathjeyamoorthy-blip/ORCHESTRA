"""
Test script to verify followup translation is working correctly.
"""

import sys
sys.path.insert(0, '.')

from agent.translator import translate_followups

# Test followups from the screenshot
test_followups = [
    "How do I apply for a new PAN card?",
    "What documents are required for PAN?",
    "How do I link Aadhaar with PAN?",
]

print("Testing Followup Translation to Tamil")
print("=" * 60)

translated_tamil = translate_followups(test_followups, "ta")

print("\nOriginal → Tamil:")
for orig, trans in zip(test_followups, translated_tamil):
    print(f"  EN: {orig}")
    print(f"  TA: {trans}")
    print()

print("\nTesting other common followups:")
other_followups = [
    "Apply for new PAN",
    "Check PAN status",
    "Link Aadhaar with PAN",
    "Continue application",
    "Start new application",
    "Show me what you know about me",
]

translated_other = translate_followups(other_followups, "ta")

for orig, trans in zip(other_followups, translated_other):
    print(f"  EN: {orig}")
    print(f"  TA: {trans}")
    print()

print("=" * 60)
print("Test complete!")
print("\nIf translations show in Tamil script, translation is working.")
print("If they remain in English, check:")
print("  1. deep-translator is installed: pip install deep-translator")
print("  2. Internet connection (for Google Translate API)")
print("  3. IndicTrans2 model is loaded (optional, better quality)")
