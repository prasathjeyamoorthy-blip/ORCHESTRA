# Bulk Optional Questions Review Feature

## Summary
Changed the optional questions reuse flow from asking "Same or New?" for EACH question individually to showing ALL saved optional questions at once and letting the user decide which ones to keep and which to change.

## Changes Made

### 1. New Bulk Review Prompt Function
**File**: `pan-rag/agent/receptionist.py`

Added `_build_individual_preferences_review_prompt()` function that:
- Shows ALL 7 optional questions with their saved answers at once
- Numbers each question (1-7) for easy reference
- Gives user 3 options:
  - **All same** - Use all previous answers
  - **Change [numbers]** - Modify specific answers (e.g., "Change 1 and 3")
  - **All new** - Answer all questions again

### 2. Bulk Review Logic in `_continue_flow()`
Replaced the individual question-by-question reuse logic with:
- **Bulk review handler** (`_pending_bulk_review` flag)
  - Parses user response (all same / all new / change specific)
  - If "all same": applies all saved answers and skips to details_collection
  - If "all new": clears saved answers and starts asking questions normally
  - If "change X and Y": applies saved answers for unchanged questions, asks only the specified ones

- **Selective question asking** (`_questions_to_ask` list)
  - Tracks which questions need to be asked after user selects specific ones to change
  - Processes answers for those questions only
  - Skips to details_collection when all selected questions are answered

### 3. Helper Functions
Added two new helper functions:

**`_ask_next_pending_question(flow)`**
- Gets the next question from `_questions_to_ask` list
- Sets current step to that question
- Returns the question prompt

**`_advance_after_answer(flow)`**
- Handles advancing to next question after user answers
- Checks if we're in selective question mode (after bulk review)
- If yes: moves to next question in `_questions_to_ask` list
- If no: uses normal flow advancement (`flow.advance_step()`)

### 4. Updated All Optional Question Handlers
Updated all 7 optional question handlers to use `_advance_after_answer(flow)` instead of `flow.advance_step(); flow.save(); return _ask_step(flow)`:
- `submission_mode`
- `delivery_mode`
- `aadhaar_photo`
- `source_of_income`
- `address_for_comm`
- `residential_status`
- `rep_assessee`

This ensures they work correctly in both normal flow and selective question mode.

### 5. Trigger Logic in `_ask_step()`
Modified `_ask_step()` to check for saved answers when entering the optional questions section:
- Triggers ONCE when reaching `submission_mode` step
- Collects all saved answers for the 7 optional questions
- If 2+ saved answers exist: shows bulk review prompt
- If < 2 saved answers: proceeds with normal flow (no reuse prompt)
- Uses `_reviewed_saved_answers` flag to ensure prompt shows only once per session

### 6. Removed Old Code
- Removed `_build_question_reuse_prompt()` function (no longer needed)
- Removed individual question reuse check loop in `_continue_flow()`
- Removed `_pending_reuse_{question}` and `_asked_reuse_{question}` flags

## User Experience

### Before (Individual Prompts)
```
Agent: I see you've answered this before!
       Submission Mode
       Your previous answer: Aadhaar-based Online (eKYC)
       Would you like to proceed with the same answer, or choose a new one?
       Reply Same or New

User: Same

Agent: I see you've answered this before!
       PAN Delivery
       Your previous answer: Physical copy to home + soft copy on email
       Would you like to proceed with the same answer, or choose a new one?
       Reply Same or New

User: Same

[... repeats for all 7 questions ...]
```

### After (Bulk Review)
```
Agent: I see you've answered these questions before! 📋

       Your previous answers:
       
       1️⃣ Submission mode: Aadhaar-based Online (eKYC)
       2️⃣ Delivery mode: Physical copy to home + soft copy on email
       3️⃣ Aadhaar photo on PAN: Yes
       4️⃣ Source of income: Salary
       5️⃣ Address for communication: Residence
       6️⃣ Residential status: Resident
       7️⃣ Representative Assessee: No
       
       Would you like to use all these answers, or change some?
       
       • Reply All same to use all previous answers
       • Reply Change [number(s)] to modify specific answers (e.g., "Change 1 and 3" or "Change 2,5,7")
       • Reply All new to answer all questions again

User: Change 2 and 3

Agent: [Asks only delivery_mode question]
User: [Answers]
Agent: [Asks only aadhaar_photo question]
User: [Answers]
Agent: Great! Now let's collect your details...
```

## Benefits
1. **Faster for returning users** - Can review and confirm all answers at once instead of 7 separate prompts
2. **More flexible** - Can selectively change specific answers without re-answering everything
3. **Better UX** - Single comprehensive view of all previous choices
4. **Less repetitive** - No more clicking "Same" 7 times in a row

## Testing Scenarios

### Scenario 1: Keep All Answers
- User has answered all 7 questions before
- User replies "All same" or "Yes" or "All"
- System applies all saved answers and skips to details_collection

### Scenario 2: Change All Answers
- User has answered all 7 questions before
- User replies "All new" or "No" or "New"
- System asks all 7 questions normally

### Scenario 3: Change Specific Answers
- User has answered all 7 questions before
- User replies "Change 1 and 3" or "Change 2,5,7"
- System applies saved answers for unchanged questions
- System asks only questions 1 and 3 (or 2, 5, 7)
- System skips to details_collection after those are answered

### Scenario 4: New User (No Saved Answers)
- User has never answered these questions before
- System does NOT show bulk review prompt
- System asks all 7 questions normally

### Scenario 5: Partial Saved Answers (< 2)
- User has answered only 1 question before
- System does NOT show bulk review prompt (threshold is 2+)
- System asks all questions normally

## Files Modified
- `pan-rag/agent/receptionist.py`

## Next Steps
1. Restart RAG server: `cd pan-rag && python main.py`
2. Test with a returning user who has answered optional questions before
3. Verify all 3 scenarios work correctly (all same, all new, change specific)
