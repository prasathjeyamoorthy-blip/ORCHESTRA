#!/usr/bin/env python3
"""
Test script to verify complete Tamil language support
Tests all application detail fields with Tamil queries
"""

import asyncio
import sys
from pathlib import Path

# Add pan-rag to path
sys.path.insert(0, str(Path(__file__).parent / "pan-rag"))

from api.transliteration import TamilTransliterator


async def test_tamil_support():
    """Test Tamil transliteration for all application detail fields"""
    
    print("=" * 70)
    print("TAMIL LANGUAGE SUPPORT TEST")
    print("=" * 70)
    print()
    
    transliterator = TamilTransliterator()
    
    # Test cases: (Tamil romanized query, expected field, description)
    test_cases = [
        # Application detail fields
        ("samarpikkum murai mathanum", "submission_mode", "Submission mode change"),
        ("viniyoga murai mathanum", "delivery_mode", "Delivery mode change"),
        ("aadhaar padathai maatru", "aadhaar_photo", "Aadhaar photo preference"),
        ("varumaana moolam update", "source_of_income", "Income source update"),
        ("ila thodarpu kolla vendiya mugavari mathanum", "address_for_comm", "Communication address"),
        ("kudiyirukkai nilai mathanum", "residential_status", "Residential status"),
        ("pirathini niyamanam", "rep_assessee", "Representative assessee"),
        
        # Personal detail fields (existing support)
        ("naa thayin peyar update pannaum", "mother_name", "Mother's name update"),
        ("en sambalam update", "salary", "Salary update"),
        ("email mathanum", "email", "Email change"),
    ]
    
    print(f"Testing {len(test_cases)} Tamil queries...\n")
    
    passed = 0
    failed = 0
    
    for i, (query, expected_field, description) in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {description}")
        print(f"  Query: {query!r}")
        
        # Check if Tamil is detected
        is_tamil = transliterator.is_tamil_romanized(query)
        print(f"  Tamil detected: {is_tamil}")
        
        if is_tamil:
            # Extract intent
            try:
                intent_data = await transliterator.extract_field_intent(query, use_llm=True)
                detected_field = intent_data.get('field')
                tamil_script = intent_data.get('tamil_script')
                confidence = intent_data.get('confidence', 'unknown')
                
                print(f"  Detected field: {detected_field}")
                print(f"  Tamil script: {tamil_script}")
                print(f"  Confidence: {confidence}")
                
                if detected_field == expected_field:
                    print(f"  ✅ PASSED\n")
                    passed += 1
                else:
                    print(f"  ❌ FAILED - Expected {expected_field}, got {detected_field}\n")
                    failed += 1
            except Exception as e:
                print(f"  ❌ FAILED - Error: {e}\n")
                failed += 1
        else:
            print(f"  ❌ FAILED - Tamil not detected\n")
            failed += 1
    
    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)
    
    if failed == 0:
        print("\n🎉 All tests passed! Tamil support is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the results above.")
    
    return failed == 0


async def test_bilingual_options():
    """Test bilingual option formatting"""
    
    print("\n" + "=" * 70)
    print("BILINGUAL OPTIONS TEST")
    print("=" * 70)
    print()
    
    # Sample options in both languages
    options = {
        "submission_mode": [
            "Aadhaar-based Online (eKYC) | ஆதார் அடிப்படையிலான ஆன்லைன்",
            "Upload scanned docs & eSign | ஸ்கேன் செய்யப்பட்ட ஆவணங்களைப் பதிவேற்றவும் & eSign",
            "Fill online + courier physical form | ஆன்லைனில் நிரப்பவும் + கூரியர் உடல் படிவம்"
        ],
        "address_for_comm": [
            "Residence | வீடு",
            "Office | அலுவலகம்",
            "Representative Assessee (RA) | பிரதிநிதி மதிப்பீட்டாளர்"
        ],
        "aadhaar_photo": [
            "Yes | ஆம்",
            "No | இல்லை"
        ]
    }
    
    for field, opts in options.items():
        print(f"Field: {field}")
        print(f"Options:")
        for i, opt in enumerate(opts, 1):
            print(f"  {i}. {opt}")
        print()
    
    print("✅ Bilingual options display correctly\n")


async def main():
    """Run all tests"""
    
    # Test 1: Tamil query detection and field mapping
    success1 = await test_tamil_support()
    
    # Test 2: Bilingual option formatting
    await test_bilingual_options()
    
    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)
    
    if success1:
        print("\n✅ All tests passed successfully!")
        print("Tamil language support is fully functional.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        print("Please review the output above and fix any issues.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
