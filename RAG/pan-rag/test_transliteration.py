#!/usr/bin/env python3
"""
Test script for Tamil transliteration and field intent extraction.
Run this to verify the transliteration module works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api.transliteration import (
    TamilTransliterator,
    handle_transliteration_request,
    format_field_update_response,
)


async def test_detection():
    """Test Tamil romanization detection."""
    print("=" * 60)
    print("TEST 1: Tamil Romanization Detection")
    print("=" * 60)
    
    transliterator = TamilTransliterator()
    
    test_cases = [
        ("naa kudiiruppu nilai update pannaum", True),
        ("en thayin peyar update pananum", True),
        ("I want to update my details", False),
        ("sambalam update pannaum", True),
        ("How do I apply for PAN?", False),
        ("en amma peyar Lakshmi", True),
    ]
    
    for text, expected in test_cases:
        result = transliterator.is_tamil_romanized(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' → {result} (expected {expected})")
    print()


async def test_intent_extraction():
    """Test intent extraction from romanized Tamil."""
    print("=" * 60)
    print("TEST 2: Intent Extraction (Rule-Based)")
    print("=" * 60)
    
    transliterator = TamilTransliterator()
    
    test_cases = [
        "naa sambalam update pannaum",
        "en thayin peyar update pananum",
        "email update seiyanum",
        "veettu mukhavari matra",
    ]
    
    for text in test_cases:
        result = transliterator._rule_based_extract_intent(text)
        print(f"\nInput: {text}")
        print(f"  Field: {result.get('field')}")
        print(f"  Intent: {result.get('intent')}")
        print(f"  Confidence: {result.get('confidence')}")
    print()


async def test_llm_extraction():
    """Test LLM-based intent extraction."""
    print("=" * 60)
    print("TEST 3: LLM Intent Extraction")
    print("=" * 60)
    print("Note: This requires the RAG server to be running")
    print()
    
    try:
        transliterator = TamilTransliterator()
        
        test_cases = [
            "naa kudiiruppu nilai update pannaum",
            "en amma peyar Lakshmi",
            "sambalam 5 lakh update pannaum",
        ]
        
        for text in test_cases:
            print(f"Input: {text}")
            try:
                result = await transliterator.extract_field_intent(text, use_llm=True)
                print(f"  Field: {result.get('field')}")
                print(f"  Value: {result.get('value')}")
                print(f"  Intent: {result.get('intent')}")
                print(f"  Confidence: {result.get('confidence')}")
                print(f"  Tamil Script: {result.get('tamil_script')}")
            except Exception as e:
                print(f"  Error: {e}")
            print()
            
    except Exception as e:
        print(f"LLM test failed: {e}")
        print("Make sure the RAG server is running on port 8000")
    print()


async def test_response_formatting():
    """Test response message formatting."""
    print("=" * 60)
    print("TEST 4: Response Formatting")
    print("=" * 60)
    
    test_cases = [
        {
            'field': 'mother_name',
            'value': 'Lakshmi',
            'intent': 'update',
            'tamil_script': 'என் அம்மா பெயர் லக்ஷ்மி',
            'confidence': 'high',
        },
        {
            'field': 'salary',
            'value': None,
            'intent': 'update',
            'tamil_script': 'நான் சம்பளம் மாற்ற வேண்டும்',
            'confidence': 'high',
        },
    ]
    
    for intent_data in test_cases:
        response = format_field_update_response(intent_data, current_value="Not set")
        print(f"\nField: {intent_data['field']}")
        print(f"Value: {intent_data['value']}")
        print(f"Response:\n{response}")
        print("-" * 40)
    print()


async def test_full_flow():
    """Test the complete transliteration flow."""
    print("=" * 60)
    print("TEST 5: Complete Flow")
    print("=" * 60)
    print("Note: This requires the RAG server to be running")
    print()
    
    test_messages = [
        "naa kudiiruppu nilai update pannaum",
        "I want to update my details",  # Should not trigger
        "en amma peyar Lakshmi",
    ]
    
    for message in test_messages:
        print(f"Message: {message}")
        try:
            result = await handle_transliteration_request(message, "test_session")
            if result:
                print(f"  ✓ Transliteration detected")
                print(f"    Field: {result.get('field')}")
                print(f"    Value: {result.get('value')}")
                print(f"    Tamil: {result.get('tamil_script')}")
            else:
                print(f"  → No transliteration (normal processing)")
        except Exception as e:
            print(f"  Error: {e}")
        print()


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Tamil Transliteration Module Test Suite")
    print("=" * 60 + "\n")
    
    await test_detection()
    await test_intent_extraction()
    await test_llm_extraction()
    await test_response_formatting()
    await test_full_flow()
    
    print("=" * 60)
    print("Test Suite Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
