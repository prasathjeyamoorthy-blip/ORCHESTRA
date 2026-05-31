# Test Queries for Stored Data Intent

## General Queries (Should Show All Data)

### Category 1: "What do you know"
- [ ] "What do you know about me?"
- [ ] "What you know about me?"
- [ ] "What do u know about me?"
- [ ] "What all do you know?"
- [ ] "What info do you have?"
- [ ] "What information do you have about me?"
- [ ] "What data do you have?"
- [ ] "What details do you have?"

### Category 2: "What did I give/tell"
- [ ] "What did I give you?"
- [ ] "What did I tell you?"
- [ ] "What did I provide?"
- [ ] "What did I share?"
- [ ] "What have I given?"
- [ ] "What have I told you?"
- [ ] "What details did I give?"
- [ ] "What info did I provide?"
- [ ] "What information i gave?"
- [ ] "What data i gave?"

### Category 3: "Show me"
- [ ] "Show me my details"
- [ ] "Show my details"
- [ ] "Show me my info"
- [ ] "Show my info"
- [ ] "Show me my data"
- [ ] "Tell me my details"
- [ ] "Give me my details"
- [ ] "List my details"

### Category 4: "Profile"
- [ ] "my profile"
- [ ] "My information"
- [ ] "My details"
- [ ] "about me"
- [ ] "show profile"
- [ ] "view profile"
- [ ] "check profile"

### Category 5: "What have you saved/stored"
- [ ] "What have you saved?"
- [ ] "What did you save?"
- [ ] "What you saved?"
- [ ] "What have you stored?"
- [ ] "What did you store?"
- [ ] "What have you remembered?"
- [ ] "What do you remember about me?"
- [ ] "What you remember about me?"

### Category 6: "Recall/retrieve"
- [ ] "Recall my details"
- [ ] "Recall my info"
- [ ] "Retrieve my details"
- [ ] "Get my details"
- [ ] "Fetch my info"

### Category 7: "Summary"
- [ ] "Give me a summary"
- [ ] "Summarize my info"
- [ ] "Overview of my details"
- [ ] "Summary of my data"

## Specific Field Queries

### Name Queries
- [ ] "What is my name?"
- [ ] "Whats my name?"
- [ ] "my name"
- [ ] "What name did I give?"
- [ ] "Do you know my name?"
- [ ] "Tell me my name"
- [ ] "Remind me my name"

### Email Queries
- [ ] "What is my email?"
- [ ] "Whats my email?"
- [ ] "my email"
- [ ] "What email did I give?"
- [ ] "My email address"
- [ ] "Tell me my email"

### Phone Queries
- [ ] "What is my phone?"
- [ ] "Whats my phone?"
- [ ] "my phone"
- [ ] "What phone did I give?"
- [ ] "My phone number"
- [ ] "My mobile"
- [ ] "My contact"
- [ ] "Tell me my phone"

### PAN Queries
- [ ] "What is my PAN?"
- [ ] "Whats my PAN?"
- [ ] "my PAN"
- [ ] "What PAN did I give?"
- [ ] "My PAN number"
- [ ] "My PAN card"
- [ ] "Do you have my PAN?"
- [ ] "Tell me my PAN"

### Aadhaar Queries
- [ ] "What is my Aadhaar?"
- [ ] "Whats my Aadhaar?"
- [ ] "my Aadhaar"
- [ ] "My Aadhaar number"
- [ ] "What Aadhaar did I give?"

### Address Queries
- [ ] "What is my address?"
- [ ] "Whats my address?"
- [ ] "my address"
- [ ] "Where do I live?"
- [ ] "My location"
- [ ] "My city"
- [ ] "Tell me my address"

### Income Queries
- [ ] "What is my income?"
- [ ] "Whats my income?"
- [ ] "my income"
- [ ] "My salary"
- [ ] "What salary did I give?"
- [ ] "How much do I earn?"
- [ ] "Tell me my income"

### DOB Queries
- [ ] "What is my DOB?"
- [ ] "Whats my DOB?"
- [ ] "My date of birth"
- [ ] "My birthday"
- [ ] "When was I born?"
- [ ] "My birth date"

### Mother's Name Queries
- [ ] "What is my mother name?"
- [ ] "Whats my mother name?"
- [ ] "My mother name"
- [ ] "My mothers name"
- [ ] "My mother's name"

## Edge Cases

### Casual/Informal Queries
- [ ] "what u know bout me"
- [ ] "wats my name"
- [ ] "show details"
- [ ] "my info"
- [ ] "profile"

### Typos
- [ ] "waht do you know"
- [ ] "whats my emial"
- [ ] "my phoen number"

### Mixed Case
- [ ] "WHAT DO YOU KNOW ABOUT ME"
- [ ] "My Profile"
- [ ] "sHoW mY dEtAiLs"

### With Extra Words
- [ ] "Can you tell me what you know about me?"
- [ ] "I want to see my profile please"
- [ ] "Could you show me my details?"
- [ ] "Please tell me what is my email"

### Conversational
- [ ] "Hey, what do you know about me?"
- [ ] "So, what's my name again?"
- [ ] "Um, can you show my details?"

## Negative Tests (Should NOT Trigger Intent)

### Similar But Different
- [ ] "What do you know about PAN?" (asking about PAN, not user)
- [ ] "Show me PAN details" (asking about PAN service)
- [ ] "What is PAN?" (general question)
- [ ] "Tell me about PAN application" (general question)

### Unrelated Queries
- [ ] "How to apply for PAN?"
- [ ] "What documents are needed?"
- [ ] "Check PAN status"
- [ ] "Link Aadhaar"

## Test Script

```bash
#!/bin/bash

# Set your access token
TOKEN="your_access_token_here"
SESSION="test-session-$(date +%s)"

# Function to test a query
test_query() {
  local query="$1"
  echo "Testing: $query"
  curl -s -X POST http://localhost:5000/api/chat \
    -H "Cookie: access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\":\"$query\",\"session_id\":\"$SESSION\"}" \
    | jq -r '.answer' | head -n 5
  echo "---"
  sleep 1
}

# Test general queries
echo "=== GENERAL QUERIES ==="
test_query "What do you know about me?"
test_query "Show me my details"
test_query "my profile"

# Test specific queries
echo "=== SPECIFIC QUERIES ==="
test_query "What is my name?"
test_query "my email"
test_query "tell me my PAN"

# Test edge cases
echo "=== EDGE CASES ==="
test_query "what u know bout me"
test_query "SHOW MY DETAILS"
test_query "Can you tell me what you know about me?"

# Test negative cases
echo "=== NEGATIVE CASES (should go to RAG) ==="
test_query "What do you know about PAN?"
test_query "How to apply for PAN?"
```

## Expected Results

### General Query Response Format
```
Here's everything I know about you:

### 👤 Personal Information
- **Name**: ...
...

### 📞 Contact Information
...

[Multiple sections with all stored data]
```

### Specific Query Response Format
```
Your [field] is: **[value]**
```

### Empty Profile Response
```
I don't have any information about you yet...
```

### Field Not Available Response
```
I don't have your [field] on record yet. Would you like to provide it?
```

## Testing Checklist

### Setup
- [ ] Backend server running
- [ ] User logged in (has valid access_token)
- [ ] User has some data in profile (name, email, etc.)
- [ ] Redis connection working

### General Queries
- [ ] Test 10+ general query variations
- [ ] Verify all sections appear in response
- [ ] Verify markdown formatting is correct
- [ ] Verify followup suggestions appear

### Specific Queries
- [ ] Test all 9 field types
- [ ] Test with data present
- [ ] Test with data missing
- [ ] Verify correct field value returned

### Edge Cases
- [ ] Test with empty profile
- [ ] Test with partial profile
- [ ] Test with typos
- [ ] Test with mixed case
- [ ] Test with extra words

### Negative Tests
- [ ] Verify unrelated queries go to RAG
- [ ] Verify PAN-related queries go to RAG
- [ ] No false positives

### Performance
- [ ] Response time < 100ms
- [ ] No errors in logs
- [ ] Memory saved correctly

### Privacy
- [ ] Only user's own data shown
- [ ] No cross-user data leakage
- [ ] Data properly isolated

## Success Criteria

✅ 95%+ of test queries correctly detected
✅ All data sections displayed correctly
✅ Specific field queries return correct values
✅ Empty profile handled gracefully
✅ No false positives (unrelated queries)
✅ Response time < 100ms
✅ No errors or crashes
✅ Privacy maintained

## Automated Test Suite

```javascript
// test/storedDataIntent.test.js

const testQueries = {
  general: [
    "What do you know about me?",
    "Show me my details",
    "my profile",
    // ... 50+ more
  ],
  specific: {
    name: ["What is my name?", "my name", ...],
    email: ["What is my email?", "my email", ...],
    // ... 9 fields
  },
  negative: [
    "What do you know about PAN?",
    "How to apply for PAN?",
    // ... 20+ more
  ]
};

describe('Stored Data Intent', () => {
  test('detects general queries', () => {
    testQueries.general.forEach(query => {
      const result = _isAskingAboutStoredData(query);
      expect(result.isAsking).toBe(true);
      expect(result.specificField).toBe(null);
    });
  });
  
  test('detects specific field queries', () => {
    Object.entries(testQueries.specific).forEach(([field, queries]) => {
      queries.forEach(query => {
        const result = _isAskingAboutStoredData(query);
        expect(result.isAsking).toBe(true);
        expect(result.specificField).toBe(field);
      });
    });
  });
  
  test('does not detect unrelated queries', () => {
    testQueries.negative.forEach(query => {
      const result = _isAskingAboutStoredData(query);
      expect(result.isAsking).toBe(false);
    });
  });
});
```

---

**Total Test Cases**: 150+
**Coverage**: General (50+), Specific (90+), Edge (20+), Negative (20+)
**Estimated Test Time**: 10-15 minutes (manual), 2-3 minutes (automated)
