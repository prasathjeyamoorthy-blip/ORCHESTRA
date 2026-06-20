"""
core/pan_flow_agent.py — PAN Registration Flow for Voice Agent

Integrates the complete PAN application flow from pan-rag/agent/receptionist.py
into the voice agent with state management and voice-friendly prompts.
"""

import re
from typing import Optional
from pathlib import Path
import json

# ── Flow Step Constants ──────────────────────────────────────────────
FLOW_STEPS = [
    "applicant_type",
    "submission_mode", 
    "delivery_mode",
    "aadhaar_photo",
    "source_of_income",
    "address_for_comm",
    "residential_status",
    "rep_assessee",
    "details_collection",
    "confirmation",
    "documents",
]

# ── Voice-friendly prompts for each step ─────────────────────────────
STEP_PROMPTS = {
    "applicant_type": {
        "en": "Are you an Indian citizen, an Indian company or entity, or a foreign individual or entity?",
        "options": {
            "indian_citizen": ["indian citizen", "citizen", "individual", "person", "myself"],
            "indian_entity": ["company", "entity", "business", "firm", "huf", "trust"],
            "foreign": ["foreign", "nri", "overseas", "abroad", "foreign citizen"],
        }
    },
    "submission_mode": {
        "en": "How would you like to submit your application? You can use Aadhaar e-sign, upload scanned documents with e-sign, or submit physical documents.",
        "options": {
            "aadhaar_esign": ["aadhaar", "esign", "aadhaar esign", "digital", "online"],
            "esign_scanned": ["scanned", "upload", "scan", "e sign scanned"],
            "physical": ["physical", "paper", "hard copy", "in person"],
        }
    },
    "delivery_mode": {
        "en": "Do you want a physical PAN card delivered to your address, or just the e-PAN sent to your email?",
        "options": {
            "physical_and_soft": ["physical", "both", "card", "mail it", "deliver", "post"],
            "soft_only": ["e-pan", "epan", "email", "digital only", "soft copy", "just email"],
        }
    },
    "aadhaar_photo": {
        "en": "Would you like to use the photo from your Aadhaar card on your PAN card?",
        "options": {
            True: ["yes", "yeah", "sure", "okay", "use aadhaar", "use it"],
            False: ["no", "nope", "different", "new photo", "upload photo"],
        }
    },
    "source_of_income": {
        "en": "What's your primary source of income? Is it salary, business income, pension, or something else?",
        "options": {
            "Salary": ["salary", "job", "employment", "employee", "salaried"],
            "Business": ["business", "self employed", "entrepreneur", "own business"],
            "Pension": ["pension", "retired", "retirement"],
            "Other": ["other", "investment", "rental", "freelance"],
        }
    },
    "address_for_comm": {
        "en": "Where should we send your correspondence? To your residence, office, or both?",
        "options": {
            "Residential": ["residence", "home", "residential", "home address"],
            "Office": ["office", "work", "workplace", "work address"],
            "Both": ["both", "residence and office"],
        }
    },
    "residential_status": {
        "en": "Are you an Indian resident or non-resident?",
        "options": {
            "Resident": ["resident", "indian resident", "living in india", "india"],
            "Non-Resident": ["non resident", "nri", "abroad", "overseas", "outside india"],
        }
    },
    "rep_assessee": {
        "en": "Are you applying as a representative assessee, or for yourself?",
        "options": {
            True: ["representative", "rep assessee", "on behalf", "for someone"],
            False: ["myself", "for me", "no", "personal", "own"],
        }
    },
    "details_collection": {
        "en": "I'll need a few personal details. What's your full name as it appears on your ID?"
    },
    "confirmation": {
        "en": "Let me confirm your details. Is everything correct?"
    },
    "documents": {
        "en": "Great! Now let's upload your documents. You'll need to upload your Aadhaar card, a photograph, and proof of address."
    },
}

# ── Salary parsing helper ────────────────────────────────────────────
def _parse_salary(text: str) -> Optional[str]:
    """
    Parse salary from voice input in various formats:
    - "6 lakh" / "6 lakhs" / "6 lpa" / "6L"
    - "50k" / "50 thousand"
    - "2 crore" / "2cr"
    - "₹5,00,000" / "Rs. 500000"
    - "six lakh fifty thousand"
    """
    text = text.strip()
    
    # Step 0: Attach space between digit and unit ("3lahks" → "3 lahks")
    text = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', text)
    
    # Normalize typos
    text = re.sub(r'\b(laksh|laks|laakh|lac|lacs|lkahs|lahks)\b', 'lakh', text, flags=re.IGNORECASE)
    
    # Pattern matching
    patterns = [
        # "6 lakh" / "6 lakhs" / "6 lpa" / "6L" / "6l"
        (r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lpa|l)\b', lambda m: float(m.group(1)) * 100000),
        # "50k" / "50K" / "50 thousand"
        (r'(\d+(?:\.\d+)?)\s*(?:k|thousand)\b', lambda m: float(m.group(1)) * 1000),
        # "2 crore" / "2cr" / "2CR"
        (r'(\d+(?:\.\d+)?)\s*(?:crore|cr)\b', lambda m: float(m.group(1)) * 10000000),
        # "₹5,00,000" / "Rs. 500000" / "INR 500000"
        (r'(?:₹|rs\.?|inr)\s*([0-9,]+)', lambda m: float(m.group(1).replace(',', ''))),
    ]
    
    for pattern, converter in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = converter(match)
            return f"₹{int(amount):,}"
    
    # Bare number ≥ 10000
    bare = re.search(r'\b(\d{5,})\b', text)
    if bare:
        return f"₹{int(bare.group(1)):,}"
    
    # Word numbers: "six lakh", "five lakh fifty thousand"
    word_map = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    }
    words = text.lower().split()
    if "lakh" in words or "thousand" in words or "crore" in words:
        total = 0
        current = 0
        for i, word in enumerate(words):
            if word in word_map:
                current += word_map[word]
            elif word in ("lakh", "lakhs"):
                total += (current or 1) * 100000
                current = 0
            elif word in ("thousand",):
                total += (current or 1) * 1000
                current = 0
            elif word in ("crore", "crores"):
                total += (current or 1) * 10000000
                current = 0
        total += current
        if total >= 1000:
            return f"₹{total:,}"
    
    return None


class PANFlowAgent:
    """
    Stateful PAN registration flow agent for voice interactions.
    Manages conversation state, collects data step-by-step, and
    provides voice-friendly prompts.
    """
    
    def __init__(self, session_id: str, state_file: Optional[Path] = None):
        self.session_id = session_id
        self.state_file = state_file or Path(f"/tmp/pan_voice_{session_id}.json")
        self.state = self._load_state()
        
    def _load_state(self) -> dict:
        """Load conversation state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "current_step": None,
            "service_id": None,
            "complete": False,
            "data": {},
        }
    
    def _save_state(self):
        """Save conversation state to disk."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save state: {e}")
    
    def has_active_flow(self) -> bool:
        """Check if there's an active PAN application flow."""
        return (
            self.state.get("service_id") == "pan_apply_indian" 
            and not self.state.get("complete")
        )
    
    def start_flow(self):
        """Start a new PAN application flow."""
        self.state = {
            "current_step": FLOW_STEPS[0],
            "service_id": "pan_apply_indian",
            "complete": False,
            "data": {},
        }
        self._save_state()
    
    def get_current_prompt(self, language: str = "en") -> str:
        """Get the voice prompt for the current step."""
        if not self.has_active_flow():
            return None
        
        step = self.state.get("current_step")
        if not step or step not in STEP_PROMPTS:
            return None
        
        prompt_data = STEP_PROMPTS[step]
        return prompt_data.get(language, prompt_data.get("en"))
    
    def process_input(self, user_input: str, language: str = "en") -> dict:
        """
        Process voice input for the current step.
        Returns: {
            "success": bool,
            "message": str,  # response to speak
            "next_prompt": str or None,  # next question if flow continues
            "complete": bool,  # True if flow is complete
        }
        """
        if not self.has_active_flow():
            return {
                "success": False,
                "message": "I'm not sure what you're asking. Would you like to apply for a PAN card?",
                "next_prompt": None,
                "complete": False,
            }
        
        step = self.state.get("current_step")
        user_input = user_input.lower().strip()
        
        # Handle each step
        if step == "applicant_type":
            return self._process_applicant_type(user_input, language)
        elif step == "submission_mode":
            return self._process_submission_mode(user_input, language)
        elif step == "delivery_mode":
            return self._process_delivery_mode(user_input, language)
        elif step == "aadhaar_photo":
            return self._process_aadhaar_photo(user_input, language)
        elif step == "source_of_income":
            return self._process_source_of_income(user_input, language)
        elif step == "address_for_comm":
            return self._process_address_for_comm(user_input, language)
        elif step == "residential_status":
            return self._process_residential_status(user_input, language)
        elif step == "rep_assessee":
            return self._process_rep_assessee(user_input, language)
        elif step == "details_collection":
            return self._process_details_collection(user_input, language)
        elif step == "confirmation":
            return self._process_confirmation(user_input, language)
        elif step == "documents":
            return self._process_documents(user_input, language)
        
        return {
            "success": False,
            "message": "I'm having trouble understanding. Could you say that again?",
            "next_prompt": self.get_current_prompt(language),
            "complete": False,
        }
    
    def _match_option(self, user_input: str, options: dict) -> Optional[str]:
        """Match user input to predefined options using keywords."""
        user_input = user_input.lower().strip()
        for value, keywords in options.items():
            for keyword in keywords:
                if keyword.lower() in user_input:
                    return value
        return None
    
    def _advance_to_next_step(self):
        """Move to the next step in the flow."""
        current = self.state.get("current_step")
        if current in FLOW_STEPS:
            idx = FLOW_STEPS.index(current)
            if idx + 1 < len(FLOW_STEPS):
                self.state["current_step"] = FLOW_STEPS[idx + 1]
            else:
                self.state["complete"] = True
        self._save_state()
    
    def _process_applicant_type(self, user_input: str, language: str) -> dict:
        """Process applicant type selection."""
        options = STEP_PROMPTS["applicant_type"]["options"]
        matched = self._match_option(user_input, options)
        
        if matched:
            self.state["data"]["applicant_type"] = matched
            self._advance_to_next_step()
            return {
                "success": True,
                "message": "Got it. " + self.get_current_prompt(language),
                "next_prompt": self.get_current_prompt(language),
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "I didn't quite catch that. Are you an Indian citizen, a company, or a foreign individual?",
            "next_prompt": STEP_PROMPTS["applicant_type"]["en"],
            "complete": False,
        }
    
    def _process_submission_mode(self, user_input: str, language: str) -> dict:
        """Process submission mode selection."""
        options = STEP_PROMPTS["submission_mode"]["options"]
        matched = self._match_option(user_input, options)
        
        if matched:
            self.state["data"]["submission_mode"] = matched
            self._advance_to_next_step()
            return {
                "success": True,
                "message": "Perfect. " + self.get_current_prompt(language),
                "next_prompt": self.get_current_prompt(language),
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "I'm not sure which option you chose. Say Aadhaar e-sign, scanned documents, or physical documents.",
            "next_prompt": STEP_PROMPTS["submission_mode"]["en"],
            "complete": False,
        }
    
    def _process_delivery_mode(self, user_input: str, language: str) -> dict:
        """Process delivery mode selection."""
        options = STEP_PROMPTS["delivery_mode"]["options"]
        matched = self._match_option(user_input, options)
        
        if matched:
            self.state["data"]["delivery_mode"] = matched
            self._advance_to_next_step()
            return {
                "success": True,
                "message": "Understood. " + self.get_current_prompt(language),
                "next_prompt": self.get_current_prompt(language),
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "Sorry, I didn't get that. Do you want a physical card or just e-PAN by email?",
            "next_prompt": STEP_PROMPTS["delivery_mode"]["en"],
            "complete": False,
        }
    
    def _process_aadhaar_photo(self, user_input: str, language: str) -> dict:
        """Process Aadhaar photo decision."""
        options = STEP_PROMPTS["aadhaar_photo"]["options"]
        matched = self._match_option(user_input, options)
        
        if matched is not None:
            self.state["data"]["aadhaar_photo"] = matched
            self._advance_to_next_step()
            return {
                "success": True,
                "message": "Okay. " + self.get_current_prompt(language),
                "next_prompt": self.get_current_prompt(language),
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "Just say yes or no. Do you want to use your Aadhaar photo?",
            "next_prompt": STEP_PROMPTS["aadhaar_photo"]["en"],
            "complete": False,
        }
    
    def _process_source_of_income(self, user_input: str, language: str) -> dict:
        """Process source of income selection."""
        options = STEP_PROMPTS["source_of_income"]["options"]
        matched = self._match_option(user_input, options)
        
        if matched:
            self.state["data"]["source_of_income"] = matched
            self._advance_to_next_step()
            return {
                "success": True,
                "message": "Got it. " + self.get_current_prompt(language),
                "next_prompt": self.get_current_prompt(language),
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "Sorry, I'm not sure. Is your income from salary, business, pension, or something else?",
            "next_prompt": STEP_PROMPTS["source_of_income"]["en"],
            "complete": False,
        }
    
    def _process_address_for_comm(self, user_input: str, language: str) -> dict:
        """Process address for communication selection."""
        options = STEP_PROMPTS["address_for_comm"]["options"]
        matched = self._match_option(user_input, options)
        
        if matched:
            self.state["data"]["address_for_comm"] = matched
            self._advance_to_next_step()
            return {
                "success": True,
                "message": "Alright. " + self.get_current_prompt(language),
                "next_prompt": self.get_current_prompt(language),
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "I didn't catch that. Should we send mail to your home, office, or both?",
            "next_prompt": STEP_PROMPTS["address_for_comm"]["en"],
            "complete": False,
        }
    
    def _process_residential_status(self, user_input: str, language: str) -> dict:
        """Process residential status selection."""
        options = STEP_PROMPTS["residential_status"]["options"]
        matched = self._match_option(user_input, options)
        
        if matched:
            self.state["data"]["residential_status"] = matched
            self._advance_to_next_step()
            return {
                "success": True,
                "message": "Noted. " + self.get_current_prompt(language),
                "next_prompt": self.get_current_prompt(language),
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "I'm not sure. Are you a resident of India or non-resident?",
            "next_prompt": STEP_PROMPTS["residential_status"]["en"],
            "complete": False,
        }
    
    def _process_rep_assessee(self, user_input: str, language: str) -> dict:
        """Process representative assessee decision."""
        options = STEP_PROMPTS["rep_assessee"]["options"]
        matched = self._match_option(user_input, options)
        
        if matched is not None:
            self.state["data"]["rep_assessee"] = matched
            self._advance_to_next_step()
            # Start collecting personal details
            self.state["details_step"] = "full_name"
            self._save_state()
            return {
                "success": True,
                "message": "Perfect. Now I need a few personal details. What's your full name as it appears on your ID?",
                "next_prompt": None,
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "Just say yes or no. Are you applying as a representative assessee?",
            "next_prompt": STEP_PROMPTS["rep_assessee"]["en"],
            "complete": False,
        }
    
    def _process_details_collection(self, user_input: str, language: str) -> dict:
        """Process personal details collection (multi-turn)."""
        details_step = self.state.get("details_step")
        
        if details_step == "full_name":
            # Extract name from input
            name = user_input.strip()
            # Remove common filler words
            name = re.sub(r'\b(my name is|i am|it is|it\'s|its)\b', '', name, flags=re.IGNORECASE).strip()
            name = re.sub(r'\b(as)\b', '', name, flags=re.IGNORECASE).strip()
            
            if len(name) > 2:
                self.state["data"]["full_name"] = name.title()
                self.state["details_step"] = "mother_name"
                self._save_state()
                return {
                    "success": True,
                    "message": f"Thank you. And what's your mother's full name?",
                    "next_prompt": None,
                    "complete": False,
                }
            
            return {
                "success": False,
                "message": "I didn't catch your name. Could you say that again?",
                "next_prompt": None,
                "complete": False,
            }
        
        elif details_step == "mother_name":
            name = user_input.strip()
            name = re.sub(r'\b(my mother\'?s? name is|her name is|it is|it\'s|its)\b', '', name, flags=re.IGNORECASE).strip()
            name = re.sub(r'\b(as)\b', '', name, flags=re.IGNORECASE).strip()
            
            if len(name) > 2:
                self.state["data"]["mother_name"] = name.title()
                self.state["details_step"] = "email"
                self._save_state()
                return {
                    "success": True,
                    "message": "Got it. What's your email address?",
                    "next_prompt": None,
                    "complete": False,
                }
            
            return {
                "success": False,
                "message": "Sorry, I didn't get that. What's your mother's name?",
                "next_prompt": None,
                "complete": False,
            }
        
        elif details_step == "email":
            # Extract email
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_input)
            if email_match:
                self.state["data"]["email"] = email_match.group(0).lower()
                self.state["details_step"] = "salary"
                self._save_state()
                return {
                    "success": True,
                    "message": "Perfect. And what's your annual income or salary?",
                    "next_prompt": None,
                    "complete": False,
                }
            
            return {
                "success": False,
                "message": "I couldn't hear a valid email. Could you spell it out?",
                "next_prompt": None,
                "complete": False,
            }
        
        elif details_step == "salary":
            salary = _parse_salary(user_input)
            if salary:
                self.state["data"]["salary"] = salary
                self.state["details_step"] = None
                self._advance_to_next_step()
                return {
                    "success": True,
                    "message": f"Thanks. Let me confirm your details. " + self._build_confirmation_summary(),
                    "next_prompt": None,
                    "complete": False,
                }
            
            return {
                "success": False,
                "message": "I didn't understand the amount. Could you say it again? Like six lakh or 6 L P A?",
                "next_prompt": None,
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "I'm not sure where we are. Let me start over with your name.",
            "next_prompt": None,
            "complete": False,
        }
    
    def _build_confirmation_summary(self) -> str:
        """Build a voice-friendly summary of collected data."""
        data = self.state.get("data", {})
        parts = []
        
        if data.get("full_name"):
            parts.append(f"Your name is {data['full_name']}")
        if data.get("mother_name"):
            parts.append(f"Mother's name {data['mother_name']}")
        if data.get("email"):
            parts.append(f"Email {data['email']}")
        if data.get("salary"):
            parts.append(f"Annual income {data['salary']}")
        
        summary = ", ".join(parts) + ". Is everything correct? Say yes to proceed or tell me what to change."
        return summary
    
    def _process_confirmation(self, user_input: str, language: str) -> dict:
        """Process confirmation step."""
        if any(word in user_input for word in ["yes", "yeah", "correct", "right", "perfect", "proceed"]):
            self._advance_to_next_step()
            return {
                "success": True,
                "message": "Excellent! Now let's upload your documents. I'll need your Aadhaar card, a recent photograph, and proof of address. You can upload them through the app interface.",
                "next_prompt": None,
                "complete": False,
            }
        elif any(word in user_input for word in ["no", "wrong", "change", "update", "fix"]):
            # Allow user to specify what to change
            return {
                "success": False,
                "message": "What would you like to change? Say your name, mother's name, email, or salary.",
                "next_prompt": None,
                "complete": False,
            }
        
        return {
            "success": False,
            "message": "Just say yes to confirm or tell me what needs to be changed.",
            "next_prompt": None,
            "complete": False,
        }
    
    def _process_documents(self, user_input: str, language: str) -> dict:
        """Process documents step."""
        # Documents are typically uploaded through UI, not voice
        # Voice agent can guide user to the upload interface
        if any(word in user_input for word in ["uploaded", "done", "attached", "sent"]):
            self.state["complete"] = True
            self._save_state()
            return {
                "success": True,
                "message": "Great! Your application is now complete. You should receive your e-PAN within 48 hours at your email address. Is there anything else I can help you with?",
                "next_prompt": None,
                "complete": True,
            }
        
        return {
            "success": True,
            "message": "Use the upload button in the app to attach your documents. Let me know when you're done.",
            "next_prompt": None,
            "complete": False,
        }
    
    def reset(self):
        """Reset the flow and start over."""
        self.state = {
            "current_step": None,
            "service_id": None,
            "complete": False,
            "data": {},
        }
        self._save_state()
