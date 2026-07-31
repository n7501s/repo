import os
import json

STATE_FILE = "router_state.json"

def load_progress():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed_comments": 0, "last_summary": ""}

def save_progress(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving progress: {e}")

def process_large_chatgpt_history(history_text, chunk_size=10000):
    return [history_text[i:i+chunk_size] for i in range(0, len(history_text), chunk_size)]
