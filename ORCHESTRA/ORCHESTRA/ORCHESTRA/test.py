from agent import agentic_rag

state = {
    "question": "What is the Access Type for the Residence Certificate?",
    "intent": None,
    "context": None,
    "answer": None,
    "applicant_category": None,
    "stage": None
}

state = agentic_rag.invoke(state)

print(state["answer"])
print("STAGE:", state["stage"])