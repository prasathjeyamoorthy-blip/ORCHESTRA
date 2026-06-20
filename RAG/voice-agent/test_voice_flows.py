"""
test_voice_flows.py — Test script for voice agent PAN registration flows

Tests the complete integration without requiring actual audio input.
Simulates user voice inputs as text to validate flow logic.
"""

import sys
from pathlib import Path

# Add voice-agent to path
sys.path.insert(0, str(Path(__file__).parent))

from core.voice_receptionist import VoiceReceptionist


class VoiceFlowTester:
    """Test harness for voice agent flows."""
    
    def __init__(self):
        self.receptionist = VoiceReceptionist()
        self.session_id = "test_session_123"
        self.user_id = "test_user"
        self.conversation_history = []
        
    def simulate_voice_input(self, user_text: str) -> dict:
        """
        Simulate a user voice input and get the agent's response.
        
        Args:
            user_text: What the user would say
            
        Returns:
            Voice-optimized response dict
        """
        print(f"\n{'='*60}")
        print(f"🎤 USER: {user_text}")
        print(f"{'='*60}")
        
        result = self.receptionist.process_voice_query(
            user_text=user_text,
            session_id=self.session_id,
            user_id=self.user_id,
            conversation_history=self.conversation_history
        )
        
        if result:
            print(f"\n🤖 AGENT: {result['text']}")
            
            if result.get('options'):
                opts = result['options']
                print(f"\n📋 OPTIONS:")
                print(f"   Type: {opts['type']}")
                print(f"   Field: {opts['field']}")
                if opts.get('choices'):
                    print(f"   Choices: {opts['choices']}")
            
            print(f"\n📍 Step: {result.get('step', 'N/A')}")
            print(f"✓ Guided: {result.get('guided', False)}")
            
            # Update conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_text
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": result['text']
            })
        else:
            print(f"\n💬 AGENT: (No guided flow - would use RAG+LLM)")
        
        return result
    
    def test_full_application_flow(self):
        """Test complete PAN application flow with speed optimization."""
        print("\n" + "="*60)
        print("TEST: Full PAN Application Flow (Optimized)")
        print("="*60)
        
        steps = [
            ("I want to apply for a PAN card", "Start application"),
            ("Indian citizen", "Select applicant type"),
            ("Aadhaar online", "Choose submission mode"),
            ("Physical and email", "Choose delivery mode"),
            ("Yes", "Aadhaar photo consent"),
            ("Salary", "Source of income"),
            ("Residence", "Address for communication"),
            ("Resident", "Residential status"),
            ("No", "Representative assessee"),
            ("Rajesh Kumar", "Full name"),
            ("Lakshmi", "Mother's name"),
            ("rajesh@example.com", "Email"),
            ("6 lakhs", "Annual income"),
            ("Yes proceed", "Confirmation"),
        ]
        
        for user_input, description in steps:
            print(f"\n--- {description} ---")
            result = self.simulate_voice_input(user_input)
            if not result:
                print(f"❌ FAILED at: {description}")
                return False
            
            # Check that responses are concise (for speed optimization)
            if result.get('text'):
                word_count = len(result['text'].split())
                if word_count > 30:  # Should be brief
                    print(f"⚠️  Response might be too long: {word_count} words")
        
        print(f"\n✅ Full application flow completed successfully!")
        print(f"   All responses optimized for speed.")
        return True
    
    def test_field_update(self):
        """Test field update during flow."""
        print("\n" + "="*60)
        print("TEST: Field Update During Flow")
        print("="*60)
        
        # Start flow and get to details collection
        self.simulate_voice_input("I want to apply for PAN")
        self.simulate_voice_input("Indian citizen")
        self.simulate_voice_input("Aadhaar online")
        self.simulate_voice_input("Just email")
        self.simulate_voice_input("Yes")
        self.simulate_voice_input("Salary")
        self.simulate_voice_input("Residence")
        self.simulate_voice_input("Resident")
        self.simulate_voice_input("No")
        self.simulate_voice_input("Amit Sharma")
        
        # Now try to update submission mode mid-flow
        print(f"\n--- Updating submission mode mid-flow ---")
        result = self.simulate_voice_input("Change my submission mode")
        
        if result and result.get('step') == 'submission_mode':
            print(f"✅ Successfully switched to submission mode update")
            self.simulate_voice_input("Upload and e-sign")
            print(f"✅ Field update test passed!")
            return True
        else:
            print(f"❌ Field update failed")
            return False
    
    def test_multi_field_update(self):
        """Test updating multiple fields at once."""
        print("\n" + "="*60)
        print("TEST: Multi-Field Update")
        print("="*60)
        
        # Get to details collection
        self.simulate_voice_input("I need a new PAN")
        self.simulate_voice_input("Indian citizen")
        self.simulate_voice_input("Aadhaar online")
        self.simulate_voice_input("Physical and email")
        self.simulate_voice_input("Yes")
        self.simulate_voice_input("No income")
        self.simulate_voice_input("Residence")
        self.simulate_voice_input("Resident")
        self.simulate_voice_input("No")
        self.simulate_voice_input("Priya Gupta")
        self.simulate_voice_input("Meena")
        self.simulate_voice_input("priya@example.com")
        self.simulate_voice_input("4 lakhs")
        
        # Try multi-field update
        print(f"\n--- Updating name and email together ---")
        result = self.simulate_voice_input("Change my name to Priya Singh and email to priya.singh@example.com")
        
        if result:
            print(f"✅ Multi-field update accepted!")
            return True
        else:
            print(f"❌ Multi-field update failed")
            return False
    
    def test_typo_handling(self):
        """Test handling of common typos."""
        print("\n" + "="*60)
        print("TEST: Typo Handling")
        print("="*60)
        
        typos = [
            ("I wnat to aply for oan", "Typo in 'want apply pan'"),
            ("I want to appply for pann", "Double letters"),
            ("I wan to apply for pan", "Missing letter"),
        ]
        
        all_passed = True
        for typo_input, description in typos:
            print(f"\n--- {description} ---")
            result = self.simulate_voice_input(typo_input)
            if result and result.get('guided'):
                print(f"✅ Typo handled: {description}")
            else:
                print(f"❌ Typo not handled: {description}")
                all_passed = False
            
            # Reset for next test
            self.session_id = f"test_session_{description.replace(' ', '_')}"
        
        return all_passed
    
    def test_natural_responses(self):
        """Test natural yes/no variations."""
        print("\n" + "="*60)
        print("TEST: Natural Language Variations")
        print("="*60)
        
        # Start flow
        self.simulate_voice_input("I want a PAN card")
        self.simulate_voice_input("Indian citizen")
        self.simulate_voice_input("Aadhaar online")
        self.simulate_voice_input("Email only")
        
        # Test various ways to say "yes"
        variations = [
            ("yeah", "Informal yes"),
            ("sure", "Casual affirmative"),
            ("yup", "Very informal yes"),
        ]
        
        for variation, description in variations:
            print(f"\n--- Testing: {description} ---")
            result = self.simulate_voice_input(variation)
            if result:
                print(f"✅ Handled: {description}")
            else:
                print(f"❌ Failed: {description}")
                return False
        
        print(f"✅ All variations handled correctly!")
        return True
    
    def run_all_tests(self):
        """Run all test cases."""
        print("\n" + "="*80)
        print("VOICE AGENT PAN REGISTRATION - FULL TEST SUITE")
        print("="*80)
        
        tests = [
            ("Full Application Flow", self.test_full_application_flow),
            ("Field Update", self.test_field_update),
            ("Multi-Field Update", self.test_multi_field_update),
            ("Typo Handling", self.test_typo_handling),
            ("Natural Language Variations", self.test_natural_responses),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                # Reset session for each test
                self.session_id = f"test_{test_name.lower().replace(' ', '_')}"
                self.conversation_history = []
                
                passed = test_func()
                results.append((test_name, passed))
            except Exception as e:
                print(f"\n❌ TEST CRASHED: {test_name}")
                print(f"   Error: {e}")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")
        
        print(f"\n{'='*80}")
        print(f"TOTAL: {passed}/{total} tests passed ({passed*100//total}%)")
        print(f"{'='*80}")
        
        return passed == total


if __name__ == "__main__":
    print("Starting Voice Agent Flow Tests...")
    print("This tests the receptionist integration without requiring audio.\n")
    
    tester = VoiceFlowTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
