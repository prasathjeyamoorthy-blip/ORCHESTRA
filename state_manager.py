FIELDS = [
    ("full_name", "What is your full name?"),
    ("dob", "Enter your date of birth (DD-MM-YYYY)"),
    ("address", "Enter your complete residential address"),
    ("stay_months", "How long have you stayed here (in months)?"),
    ("purpose", "What is the purpose of this certificate?")

]

def get_current_field(state):
    for f, _ in FIELDS:
        if state[f] is None:
            return f
    return None

def get_next_question(state):
    for f, q in FIELDS:
        if state[f] is None:
            return q
    return "Done"
