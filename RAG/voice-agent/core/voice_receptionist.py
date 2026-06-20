"""
core/voice_receptionist.py — Voice-Optimized PAN Registration Receptionist

Adapts the pan-rag receptionist's guided flows for voice interactions.
Converts visual guided flows (buttons, options, forms) into conversational
voice prompts that Aria can speak naturally.
"""

import sys
import re
from pathlib import Path

# Add pan-rag to Python path so we can import its modules
PAN_RAG_PATH = Path(__file__).parent.parent.parent / "pan-rag"
sys.path.insert(0, str(PAN_RAG_PATH))

from agent.receptionist import handle_message as handle_question
from agent.flow_manager import FlowManager


class VoiceReceptionist:
    """
    Wraps pan-rag receptionist for voice interactions.
    Converts guided flow responses into voice-friendly prompts.
    """

    def __init__(self):
        self._active_sessions = {}  # session_id → FlowManager
        print("  ✅ Voice Receptionist ready — PAN registration flows loaded")

    def process_voice_query(
        self,
        user_text: str,
        session_id: str,
        user_id: str = "voice_user",
        conversation_history: list = None
    ) -> dict:
        """
        Process a voice query through the PAN registration receptionist.
        
        Args:
            user_text: User's spoken input (transcribed)
            session_id: Unique session identifier
            user_id: User identifier (for profile loading)
            conversation_history: Previous conversation context
            
        Returns:
            dict with:
                - text: Voice-friendly response text (for TTS)
                - options: List of available choices (for voice selection)
                - step: Current flow step
                - complete: Whether flow is complete
        """
        # Call the pan-rag receptionist
        result = handle_question(
            question=user_text,
            session_id=session_id,
            user_id=user_id,
            language="en",
            user_context="",
        )

        if not result:
            # No guided flow — return None so normal RAG+LLM handles it
            return None

        # Convert the result to voice-friendly format
        return self._convert_to_voice_response(result)

    def _convert_to_voice_response(self, result: dict) -> dict:
        """
        Convert pan-rag receptionist response to voice-friendly format.
        
        Transforms:
        - Button options → Spoken list of choices
        - Markdown formatting → Plain speech
        - Visual cues → Verbal cues
        """
        answer = result.get("answer", "")
        options = result.get("options", {})
        step = result.get("step")
        
        # Special handling for confirmation step - make it ultra-concise
        if step == "confirmation":
            answer = self._make_confirmation_concise(answer)
        
        # Remove markdown formatting for voice
        voice_text = self._strip_markdown_for_voice(answer)
        
        # Convert options to voice-friendly list
        voice_choices = None
        if options:
            opt_type = options.get("type")
            choices = options.get("choices", [])
            field = options.get("field", "")
            
            if opt_type == "confirmation":
                # Confirmation step - just ask directly
                voice_text += " Say yes to proceed, or tell me what to change."
                voice_choices = {
                    "type": "confirmation",
                    "choices": choices,
                    "field": "confirmation"
                }
            
            elif opt_type == "radio" and choices:
                # Convert radio buttons to numbered spoken list
                voice_text = self._add_radio_choices_for_voice(voice_text, choices, field)
                voice_choices = {
                    "type": "radio",
                    "choices": choices,
                    "field": field
                }
            
            elif opt_type == "checkbox" and choices:
                # Convert checkboxes to multiple selection list
                voice_text = self._add_checkbox_choices_for_voice(voice_text, choices, field)
                voice_choices = {
                    "type": "checkbox",
                    "choices": choices,
                    "field": field
                }
            
            elif opt_type == "text":
                # Text input field
                label = options.get("label", "your answer")
                voice_text = self._add_text_prompt_for_voice(voice_text, label)
                voice_choices = {
                    "type": "text",
                    "field": field
                }

        return {
            "text": voice_text,
            "options": voice_choices,
            "step": step,
            "complete": result.get("complete", False),
            "guided": result.get("guided", False),
            "open_upload": result.get("open_upload", False)
        }

    def _make_confirmation_concise(self, answer: str) -> str:
        """
        Make confirmation summary ultra-concise for voice.
        Extract key details and present them briefly.
        """
        # Extract the important values from the confirmation text
        import re
        
        # Build a short spoken summary
        details = []
        
        # Submission mode
        sub_match = re.search(r'Submission mode:\s+\*\*([^*]+)\*\*', answer)
        if sub_match:
            details.append(f"Submission: {sub_match.group(1)}")
        
        # Delivery
        del_match = re.search(r'PAN delivery:\s+\*\*([^*]+)\*\*', answer)
        if del_match:
            details.append(f"Delivery: {del_match.group(1)}")
        
        # Name
        name_match = re.search(r'Full name[^:]*:\s+\*\*([^*]+)\*\*', answer)
        if name_match:
            details.append(f"Name: {name_match.group(1)}")
        
        # Email
        email_match = re.search(r'Email:\s+\*\*([^*]+)\*\*', answer)
        if email_match:
            details.append(f"Email: {email_match.group(1)}")
        
        # Income
        income_match = re.search(r'Annual income:\s+\*\*([^*]+)\*\*', answer)
        if income_match:
            details.append(f"Income: {income_match.group(1)}")
        
        if details:
            # Create concise summary
            summary = "Here's your application: " + ", ".join(details[:4]) + "."
            return summary
        
        # Fallback if parsing fails
        return "Here's what I collected. Ready to proceed?"

    def _strip_markdown_for_voice(self, text: str) -> str:
        """
        Remove markdown formatting and convert to natural speech.
        
        Examples:
        - **bold** → bold (just remove asterisks)
        - # Heading → Heading
        - - List item → List item
        - [link](url) → link
        """
        # Remove markdown bold/italic
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        
        # Remove markdown headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
        # Convert list markers to natural speech
        text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Remove links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove block quotes
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        
        # Convert line breaks to natural pauses
        text = re.sub(r'\n\n+', '. ', text)
        text = re.sub(r'\n', ' ', text)
        
        # Remove table formatting
        text = re.sub(r'\|', ' ', text)
        text = re.sub(r'-{3,}', '', text)
        
        # Remove emoji and icons
        text = re.sub(r'[📎✓✅📄🎯🤖]', '', text)
        
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _add_radio_choices_for_voice(self, base_text: str, choices: list, field: str) -> str:
        """
        Add radio button choices to voice text in a natural way.
        Optimized for speed - short, direct prompts.
        
        Args:
            base_text: Base question text
            choices: List of choice strings
            field: Field name for context
            
        Returns:
            Enhanced voice prompt
        """
        if not choices:
            return base_text
        
        # Context-specific voice prompts - SHORTER for faster speech
        voice_prompts = {
            "applicant_type": "Are you an Indian citizen, company or HUF, or foreign citizen?",
            "submission_mode": "Choose Aadhaar online, upload and e-sign, or fill and courier.",
            "delivery_mode": "Physical card plus email, or email only?",
            "aadhaar_photo": "Use your Aadhaar photo on the PAN card? Yes or no.",
            "address_for_comm": "Send mail to residence, office, or representative address?",
            "residential_status": "Are you resident, non-resident, or resident but not ordinarily resident?",
            "rep_assessee": "Appointing a representative? Yes or no.",
        }
        
        if field in voice_prompts:
            return voice_prompts[field]
        
        # Generic handling for other fields - keep it short
        if len(choices) == 1:
            return f"{self._shorten_choice_for_voice(choices[0])}?"
        
        if len(choices) == 2:
            # "Option A or Option B?"
            c1 = self._shorten_choice_for_voice(choices[0])
            c2 = self._shorten_choice_for_voice(choices[1])
            return f"{c1} or {c2}?"
        
        # For 3+ options, list them concisely
        prompt = ""
        for i, choice in enumerate(choices):
            short_choice = self._shorten_choice_for_voice(choice)
            if i == len(choices) - 1:
                prompt += f"or {short_choice}?"
            elif i == len(choices) - 2:
                prompt += f"{short_choice}, "
            else:
                prompt += f"{short_choice}, "
        
        return prompt

    def _add_checkbox_choices_for_voice(self, base_text: str, choices: list, field: str) -> str:
        """
        Add checkbox choices for voice (can select multiple).
        Optimized for speed - shorter prompts.
        
        Args:
            base_text: Base question text
            choices: List of choice strings
            field: Field name for context
            
        Returns:
            Enhanced voice prompt
        """
        if not choices:
            return base_text
        
        # Context-specific voice prompts - SHORTER
        if field == "source_of_income":
            return "Pick your income sources. Salary, business, house property, other sources, capital gains, or no income."
        
        # Generic handling - concise
        prompt = ""
        for i, choice in enumerate(choices):
            short_choice = self._shorten_choice_for_voice(choice)
            if i == len(choices) - 1:
                prompt += f"or {short_choice}."
            else:
                prompt += f"{short_choice}, "
        
        return prompt

    def _add_text_prompt_for_voice(self, base_text: str, label: str) -> str:
        """
        Add text input prompt for voice.
        Optimized for speed - direct questions.
        
        Args:
            base_text: Base question text
            label: Field label
            
        Returns:
            Enhanced voice prompt
        """
        # Context-specific prompts - SHORTER
        field_prompts = {
            "Full name": "Your full name as on Aadhaar?",
            "Mother's name": "Mother's name?",
            "Email": "Your email address?",
            "Annual income": "Your annual income?",
        }
        
        for key, prompt in field_prompts.items():
            if key.lower() in label.lower():
                return prompt
        
        # Generic - concise
        return f"{label}?"

    def _shorten_choice_for_voice(self, choice: str) -> str:
        """
        Shorten long choice descriptions for voice.
        
        Examples:
        - "Physical copy to home + soft copy on email (Fees applicable)" → "physical copy plus email"
        - "Upload scanned docs & eSign" → "upload and e-sign"
        """
        # Remove parenthetical notes
        choice = re.sub(r'\([^)]+\)', '', choice).strip()
        
        # Simplify common patterns
        simplifications = [
            (r'Physical copy to home \+ soft copy on email', 'physical copy plus email'),
            (r'Only soft copy on email', 'just email'),
            (r'Aadhaar-based Online \(eKYC\)', 'Aadhaar online'),
            (r'Upload scanned docs & eSign', 'upload and e-sign'),
            (r'Fill online \+ courier physical form', 'fill online and courier'),
            (r'Indian Company / HUF / Firm', 'company, HUF, or firm'),
            (r'Foreign Citizen / NRI / Overseas', 'foreign citizen or NRI'),
            (r'Income from Business / Profession', 'business or profession'),
            (r'Income from House property', 'house property'),
            (r'Income from Other sources', 'other sources'),
            (r'Resident but not ordinarily resident', 'resident but not ordinarily resident'),
            (r'Representative Assessee \(RA\)', 'representative assessee'),
        ]
        
        for pattern, replacement in simplifications:
            choice = re.sub(pattern, replacement, choice, flags=re.IGNORECASE)
        
        return choice

    def get_flow_state(self, session_id: str) -> dict:
        """Get the current flow state for a session."""
        if session_id in self._active_sessions:
            flow = self._active_sessions[session_id]
            return flow.state
        return {}

    def reset_session(self, session_id: str):
        """Reset a voice session's flow state."""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]

