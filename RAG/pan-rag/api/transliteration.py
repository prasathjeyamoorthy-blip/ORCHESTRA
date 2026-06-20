# api/transliteration.py
"""
Tamil Transliteration and Intent Extraction Module
Handles Tamil text written in English (romanized) and converts to Tamil script,
then extracts the intent to update specific application fields.
"""

import re
from typing import Optional, Dict, Any


class TamilTransliterator:
    """Handles Tamil transliteration and field intent extraction."""

    # ---------------------------------------------------------------------------
    # DETECTION PATTERNS
    # Every significant Tamil action/field word that a user could type in English.
    # Grouped by category so it's easy to extend.
    # ---------------------------------------------------------------------------
    TAMIL_PATTERNS = [
        # ── Pronouns / possessives ──────────────────────────────────────────
        r'\b(?:naa|naan|naanu|enakku|enikku|enaku|en|ennoda|namma)\b',
        r'\b(?:enakku|enikku|enaku)\b',  # "I want / for me" — common PAN intent phrase

        # ── Action verbs (change / update / want) ───────────────────────────
        r'\b(?:mathanum|maathanum|maathu|maatru|matra|maatra|maatrunga|maathrunga)\b',  # change
        r'\b(?:pannaum|pananum|pannanum|pannunga|seiyanum|seyyanum|seivom)\b',           # do/want-to-do
        r'\b(?:thiruthanum|thiruthu|thiruthunga)\b',                                     # correct/fix
        r'\b(?:pudhupikkanum|pudhuppi|update\s*pannanum)\b',                             # update
        r'\b(?:marupadisum|thirisum|thiri)\b',                                           # redo/rechoose
        r'\b(?:kudukuren|kuduppen|tharugiren|tharuvom|thaa)\b',                          # give/provide

        # ── Personal detail fields ───────────────────────────────────────────
        r'\b(?:peyar|perr)\b',                           # name
        r'\b(?:thaayin|thaay|amma|ammaa|aai)\b',         # mother
        r'\b(?:sambalam|samabalam|samblam)\b',            # salary
        r'\b(?:varumanam|varumaanam|varumaana|varumana)\b', # income
        r'\b(?:mugavari|mukhavari|mugavari|address)\b',  # address (any)
        r'\b(?:veettu|veedu|veetu)\b',                   # house/home
        r'\b(?:emailu|mail|meilu)\b',                    # email
        r'\b(?:phone|phoneu|kai\s*pesi|kaipesi)\b',      # phone

        # ── Application detail fields ────────────────────────────────────────
        # Source of income
        r'\b(?:aatharam|aadharam|varumaana\s*aatharam|varumaana\s*moolam|vrumaana\s*moolam|moolam)\b',
        # Submission mode
        r'\b(?:samarpikkum|samarpidum|samarpikka|submit\s*murai|samarpippu)\b',
        # Delivery mode
        r'\b(?:viniyoga|viniyogam|delivery\s*murai|panbu\s*murai)\b',
        # Communication address
        r'\b(?:thodarpu|thodarbu|thodar|illathodarpu)\b',
        r'\b(?:kolla\s*vendiya|kollum|koLLa)\b',
        r'\b(?:vendiya|vendiyal|vendum)\b',
        # Residential status
        r'\b(?:kudiyirukkai|kudiyiruppu|kudiyiruppu\s*nilai|kudiyirukkum)\b',
        r'\b(?:nilai|nilaiyai|nilaiya|nilamai)\b',
        # Representative assessee
        r'\b(?:pirathini|prathini|pirathini\s*niyamanam)\b',
        # Aadhaar photo
        r'\b(?:padathai|padam|pugaippadam|photo\s*maatru)\b',
        # Submission / mode (generic)
        r'\b(?:murai|muraiyai|muraiya)\b',
    ]

    # ---------------------------------------------------------------------------
    # RULE-BASED FIELD DETECTION
    # Ordered patterns — more specific phrases first.
    # Returns the field name if a phrase matches.
    # ---------------------------------------------------------------------------
    _FIELD_RULES: list[tuple[re.Pattern, str]] = []  # built in __init_subclass__ below

    # ---------------------------------------------------------------------------
    # FIELD MAPPING (keyword → field name)  — used by rule-based fallback
    # ---------------------------------------------------------------------------
    FIELD_MAPPING = {
        # Personal details
        'peyar': 'full_name',
        'perr': 'full_name',
        'name': 'full_name',
        'thaayin': 'mother_name',
        'thaay': 'mother_name',
        'amma': 'mother_name',
        'ammaa': 'mother_name',
        'aai': 'mother_name',
        'mother': 'mother_name',
        'sambalam': 'salary',
        'samabalam': 'salary',
        'samblam': 'salary',
        'varumanam': 'salary',
        'varumaanam': 'salary',
        'varumaana': 'salary',
        'varumana': 'salary',
        'income': 'salary',
        'salary': 'salary',
        'mugavari': 'address',
        'mukhavari': 'address',
        'veettu': 'address',
        'veedu': 'address',
        'veetu': 'address',
        'address': 'address',
        'emailu': 'email',
        'email': 'email',
        'mail': 'email',
        # Application details — source of income
        'aatharam': 'source_of_income',
        'aadharam': 'source_of_income',
        'moolam': 'source_of_income',
        'source': 'source_of_income',
        # Submission mode
        'samarpikkum': 'submission_mode',
        'samarpidum': 'submission_mode',
        'samarpikka': 'submission_mode',
        'submission': 'submission_mode',
        # Delivery mode
        'viniyoga': 'delivery_mode',
        'viniyogam': 'delivery_mode',
        'delivery': 'delivery_mode',
        # Communication address
        'thodarpu': 'address_for_comm',
        'thodarbu': 'address_for_comm',
        'thodar': 'address_for_comm',
        'vendiya': 'address_for_comm',
        'vendum': 'address_for_comm',
        # Residential status
        'kudiyirukkai': 'residential_status',
        'kudiyiruppu': 'residential_status',
        'residential': 'residential_status',
        # Rep assessee
        'pirathini': 'rep_assessee',
        'prathini': 'rep_assessee',
        'representative': 'rep_assessee',
        # Aadhaar photo
        'padathai': 'aadhaar_photo',
        'padam': 'aadhaar_photo',
        'pugaippadam': 'aadhaar_photo',
        'aadhaar': 'aadhaar_photo',
    }

    def is_tamil_romanized(self, text: str) -> bool:
        """Return True if the text contains any recognisable romanized-Tamil word."""
        text_lower = text.lower()
        for pattern in self.TAMIL_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------
    async def transliterate_to_tamil(self, romanized_text: str) -> str:
        """Convert romanized Tamil to Tamil script via LLM."""
        prompt = (
            "Convert the following Tamil text written in English (romanized) to proper Tamil script.\n"
            "Only provide the Tamil script output, no explanations.\n\n"
            f"Romanized Tamil: {romanized_text}\n\n"
            "Tamil Script:"
        )
        try:
            from agent.llm import get_llm
            llm = get_llm()
            response = llm.invoke(prompt)
            return (response.content if hasattr(response, 'content') else str(response)).strip()
        except Exception as e:
            print(f"[transliteration] LLM transliteration failed: {e}")
            return romanized_text  # return original as fallback

    async def extract_field_intent(self, text: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Detect which PAN field the user wants to update and what value (if any).
        Returns a dict with keys: field, value, intent, confidence, tamil_script.
        """
        # Try rule-based first — fast and reliable for common phrases
        rule_result = self._rule_based_extract_intent(text)

        # If rule-based is confident, skip the expensive LLM call
        if rule_result.get('field') and rule_result.get('confidence') == 'high':
            # Still transliterate so we can show the Tamil script
            tamil_script = await self.transliterate_to_tamil(text)
            rule_result['tamil_script'] = tamil_script
            return rule_result

        # Fall back to LLM for ambiguous inputs
        if use_llm:
            tamil_script = await self.transliterate_to_tamil(text)
            llm_result = await self._llm_extract_intent(text, tamil_script)
            if llm_result.get('field'):
                return llm_result

        # Return whatever rule-based found (may have field=None)
        return rule_result

    def _rule_based_extract_intent(self, text: str) -> Dict[str, Any]:
        """
        Fast pattern-based field detection.
        Checks from most-specific multi-word phrases down to single keywords.
        """
        tl = text.lower()

        # ── Multi-word phrase matches (ordered most-specific → least) ──────
        phrase_map: list[tuple[str, str]] = [
            # Source of income
            ('varumaana aatharam',    'source_of_income'),
            ('varumana aatharam',     'source_of_income'),
            ('varumaana aadharam',    'source_of_income'),
            ('varumana aadharam',     'source_of_income'),
            ('varumaana moolam',      'source_of_income'),
            ('varumana moolam',       'source_of_income'),
            # Submission mode
            ('samarpikkum murai',     'submission_mode'),
            ('samarpidum murai',      'submission_mode'),
            ('samarpikka murai',      'submission_mode'),
            # Delivery mode
            ('viniyoga murai',        'delivery_mode'),
            ('viniyogam murai',       'delivery_mode'),
            # Communication address
            ('thodarpu mugavari',     'address_for_comm'),
            ('thodarbu mugavari',     'address_for_comm'),
            ('thodarpu mukhavari',    'address_for_comm'),
            ('thodar mugavari',       'address_for_comm'),
            ('vendiya mugavari',      'address_for_comm'),
            ('vendiya mukhavari',     'address_for_comm'),
            # Residential status
            ('kudiyirukkai nilai',    'residential_status'),
            ('kudiyiruppu nilai',     'residential_status'),
            ('kudiyirukkai nilaima',  'residential_status'),
            # Mother name
            ('thaayin peyar',         'mother_name'),
            ('thaay peyar',           'mother_name'),
            ('amma peyar',            'mother_name'),
            # Aadhaar photo
            ('aadhaar padam',         'aadhaar_photo'),
            ('aadhaar padathai',      'aadhaar_photo'),
            ('aadhaar pugaippadam',   'aadhaar_photo'),
        ]
        for phrase, field in phrase_map:
            if phrase in tl:
                return {
                    'field': field, 'value': None,
                    'intent': 'update', 'confidence': 'high',
                    'original_text': text, 'tamil_script': None,
                }

        # ── Single-keyword fallback ──────────────────────────────────────
        field = None
        for keyword, field_name in self.FIELD_MAPPING.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', tl):
                field = field_name
                break

        return {
            'field': field, 'value': None,
            'intent': 'update' if field else 'unknown',
            'confidence': 'medium' if field else 'low',
            'original_text': text, 'tamil_script': None,
        }

    async def _llm_extract_intent(self, original_text: str, tamil_text: Optional[str]) -> Dict[str, Any]:
        """Use LLM to extract field and value when rule-based is uncertain."""
        context = f"Original: {original_text}"
        if tamil_text and tamil_text != original_text:
            context += f"\nTamil Script: {tamil_text}"

        prompt = f"""You are analyzing a user message to understand what PAN application field they want to update.

{context}

Fields available:
- full_name: Applicant full name
- mother_name: Mother's name (thaay/amma peyar)
- salary: Annual income (sambalam / varumanam)
- email: Email address
- phone: Phone number
- address: Residential address (veettu mugavari)
- submission_mode: How to submit docs (samarpikkum murai)
- delivery_mode: How to receive PAN (viniyoga murai)
- aadhaar_photo: Use Aadhaar photo on PAN (aadhaar padam)
- source_of_income: Income source (varumaana aatharam / moolam)
- address_for_comm: Communication address (thodarpu mugavari)
- residential_status: Tax residency (kudiyirukkai nilai)
- rep_assessee: Representative assessee (pirathini)

Return ONLY a JSON object:
{{
    "field": "field_name or null",
    "value": "extracted value or null",
    "intent": "update",
    "confidence": "high/medium/low",
    "tamil_script": "tamil script if applicable"
}}

JSON:"""

        try:
            from agent.llm import get_llm
            import json
            llm = get_llm()
            response = llm.invoke(prompt)
            result_text = (response.content if hasattr(response, 'content') else str(response)).strip()

            # Strip markdown code fences if present
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            result = json.loads(result_text)
            result['original_text'] = original_text
            if tamil_text:
                result.setdefault('tamil_script', tamil_text)
            return result

        except Exception as e:
            print(f"[transliteration] LLM intent extraction failed: {e}")
            return {
                'field': None, 'value': None, 'intent': 'unknown',
                'confidence': 'low', 'original_text': original_text, 'tamil_script': tamil_text,
            }


# ---------------------------------------------------------------------------
# Module-level entry point called from routes.py
# ---------------------------------------------------------------------------
async def handle_transliteration_request(message: str, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Check if message is romanized Tamil with a field-update intent.
    Returns the intent dict if detected, None otherwise.
    """
    transliterator = TamilTransliterator()

    if not transliterator.is_tamil_romanized(message):
        return None

    # Short-circuit: if the message is a PAN service intent (apply/want PAN),
    # not a field-update, skip the expensive LLM call entirely.
    _PAN_INTENT_RE = re.compile(
        r'\b(?:pan\s+(?:card\s+)?(?:venum|vendum|edukkanum|thaa|pannanum|pnnanum|seiyanum|apply|register)|'
        r'(?:enakku|enikku|enaku|naan|naanu|naa)\s+pan|'
        r'pan\s+card\s+\w{1,5}\s+(?:apply|register))\b',
        re.IGNORECASE
    )
    if _PAN_INTENT_RE.search(message):
        return None  # Let normal flow handle it

    intent_data = await transliterator.extract_field_intent(message, use_llm=True)

    # Accept result if we have a field, regardless of confidence level
    if intent_data.get('field'):
        return intent_data

    return None


# ---------------------------------------------------------------------------
# Response formatter
# ---------------------------------------------------------------------------
def format_field_update_response(intent_data: Dict[str, Any], current_value: Optional[str] = None) -> str:
    field        = intent_data.get('field', 'unknown')
    value        = intent_data.get('value')
    tamil_script = intent_data.get('tamil_script')

    field_names = {
        'full_name':          "Full Name",
        'mother_name':        "Mother's Name",
        'salary':             "Annual Income",
        'email':              "Email Address",
        'phone':              "Phone Number",
        'address':            "Residential Address",
        'submission_mode':    "Submission Mode",
        'delivery_mode':      "PAN Delivery Mode",
        'aadhaar_photo':      "Aadhaar Photo on PAN",
        'source_of_income':   "Source of Income",
        'address_for_comm':   "Address for Communication",
        'residential_status': "Residential Status",
        'rep_assessee':       "Representative Assessee",
    }

    field_options = {
        'submission_mode': [
            "1. Aadhaar-based Online (eKYC)",
            "2. Upload scanned docs & eSign",
            "3. Fill online + courier physical form",
        ],
        'delivery_mode': [
            "1. Physical copy to home + soft copy on email (Fees applicable)",
            "2. Only soft copy on email (Fees applicable)",
        ],
        'aadhaar_photo': [
            "• Yes — use my Aadhaar photo on PAN card",
            "• No — I'll provide a separate photograph",
        ],
        'source_of_income': [
            "• Salary | சம்பளம்",
            "• Income from Business / Profession | வணிகம் / தொழில்",
            "• Income from House property | வீட்டு சொத்து",
            "• Income from Other sources | பிற மூலங்கள்",
            "• Capital Gains | மூலதன ஆதாயங்கள்",
            "• No income | வருமானம் இல்லை",
        ],
        'address_for_comm': [
            "1. Residence | வீடு",
            "2. Office | அலுவலகம்",
            "3. Representative Assessee (RA)",
        ],
        'residential_status': [
            "1. Resident | குடியிருப்பாளர்",
            "2. Non-resident | குடியுரிமை இல்லாதவர்",
            "3. Resident but not ordinarily resident",
        ],
        'rep_assessee': [
            "• Yes — applying on behalf of someone else",
            "• No — applying for myself",
        ],
    }

    field_display = field_names.get(field, field.replace('_', ' ').title())
    parts = []

    if tamil_script and tamil_script != intent_data.get('original_text'):
        parts.append(f"*{tamil_script}*\n")

    if value:
        parts.append(f"I understand you want to set your **{field_display}** to: **{value}**")
        if current_value and current_value != value:
            parts.append(f"\n*(Current value: {current_value})*")
    else:
        parts.append(f"I understand you want to update your **{field_display}**.")
        if current_value:
            parts.append(f"\nCurrent value: **{current_value}**")

        if field in field_options:
            parts.append(f"\n\n**Available options:**\n" + "\n".join(field_options[field]))
            parts.append("\nPlease select one of the options above.")
        else:
            parts.append(f"\n\nPlease provide the new value for {field_display}.")

    return "\n".join(parts)
