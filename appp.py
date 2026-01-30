from flask import Flask, request, jsonify, render_template
from llm_agent import llm_parse
from state_manager import get_current_field, get_next_question
import sqlite3
#from agent1_intent import detect_intent
# rag_agent import rag_answer


'''intent = detect_intent(user_msg)

if intent == "APPLY":
    return jsonify({"route": "agent2"})

elif intent == "QUERY":
    return jsonify({"route": "rag"})

elif intent == "STATUS":
    return jsonify({"route": "status"})

elif intent == "EXIT":
    return jsonify({"reply": "Thank you. Session ended."})'''


app = Flask(__name__, template_folder="../frontend1/templates",
            static_folder="../frontend1/static")

state = {
    "full_name": None,
    "dob": None,
    "address": None,
    "stay_months":None,
    "purpose":None
}

from database import init_db
init_db()

def save_to_db(data):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO applications (full_name, dob, address,stay_months,purpose)
            VALUES (?, ?, ?,?,?)
        ''', (data['full_name'], data['dob'], data['address'],data['stay_months'],data['purpose']))
        conn.commit()
        conn.close()
        print(" Data saved to database successfully.")
    except Exception as e:
        print(" DB Error:", e)





@app.route("/")
def home():
    return render_template("index1.html")

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json["message"]

    field = get_current_field(state)
    if field:
        data = llm_parse(msg, field)
        if field in data:
            state[field] = data[field]
    
    next_q=get_next_question(state)
    if next_q == "Done":
        save_to_db(state)
    return jsonify({"reply": get_next_question(state),"Done": next_q == "Done"})


@app.route("/admin/view")
def view_data():
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        # Select all columns from your table
        cursor.execute("SELECT id, full_name, dob, address, stay_months, purpose, timestamp FROM applications")
        rows = cursor.fetchall()
        conn.close()
        
        # Pass the database rows to the HTML template
        return render_template("admin.html", data=rows)
    except Exception as e:
        return f"Database Error: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True) 

