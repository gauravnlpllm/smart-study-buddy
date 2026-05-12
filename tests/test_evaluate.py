import os
import sys

# Ensure smart_buddy package path is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import SmartStudyBuddy
from modules.quiz_generator import Question

app = SmartStudyBuddy()

q = Question(
    question_text="Who founded the Maurya dynasty in 321 BCE?",
    options=["Chandragupta Maurya", "Bindusara", "Ashoka", "Chanakya"],
    correct_answer="A",
    explanation="Chandragupta Maurya founded the Maurya dynasty."
)

cases = [
    "A",
    "A.",
    "A. Chandragupta Maurya",
    "Chandragupta Maurya",
    "a",
    "a) Chandragupta Maurya",
    "B",
]

for c in cases:
    import re
    s_raw = c.strip()
    s = re.sub(r"\s+", " ", s_raw).strip().lower()
    print('\n---')
    print('Input raw:', repr(s_raw), 'normalized:', repr(s))
    for idx, opt in enumerate(q.options):
        opt_norm = re.sub(r"\s+", " ", (opt or "")).strip().lower()
        print(f'Option {idx} raw: {repr(opt)} -> norm: {repr(opt_norm)}')
    # Run the same normalization locally in the test to compare
    def normalize_local(q, ans):
        if not ans:
            return None
        s_raw2 = ans.strip()
        m2 = re.match(r"^\s*([A-Da-d])\s*[\.|\)]?\s*(.*)$", s_raw2)
        if m2:
            return m2.group(1).upper()
        s2 = re.sub(r"\s+", " ", s_raw2).strip().lower()
        for idx2, opt2 in enumerate(q.options or []):
            opt_norm2 = re.sub(r"\s+", " ", (opt2 or "")).strip().lower()
            if s2 == opt_norm2 or s2 in opt_norm2 or opt_norm2 in s2:
                print('DEBUG match idx:', idx2, 'opt:', opt2, 'opt_norm:', opt_norm2)
                return chr(ord('A') + idx2)
        return None

    print('normalize_local ->', normalize_local(q, c))
    res = app.evaluate_answer(q, c)
    print(f"Result: Input: {c!r} -> is_correct: {res['is_correct']}")
