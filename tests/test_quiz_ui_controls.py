import pathlib
import sys

html_path = pathlib.Path(__file__).resolve().parents[1] / "index.html"
html = html_path.read_text()

required = [
    "quiz-group-controls",
    "quiz-toggle",
    "theme-toggle",
    "theme-label",
    "quizzes-grid",
]

missing = [item for item in required if item not in html]
if missing:
    print("Missing quiz UI control markers:")
    for item in missing:
        print(f"- {item}")
    sys.exit(1)

print("OK: Quiz controls and theme toggle markers present.")
