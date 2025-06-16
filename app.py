
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import re
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text(file_bytes):
    text = ""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def is_fact_line(line):
    return any(x in line for x in [":", "-", "→", "->", "—", "=", "types", "adopted", "added", "date"])

def clean_line(line):
    return re.sub(r"[^\w\s:\-→–=]", "", line).strip()

def generate_rule_based_questions(text, max_q=10):
    lines = [clean_line(l) for l in text.splitlines() if len(l.strip()) > 15 and is_fact_line(l)]
    used = set()
    questions = []
    random.shuffle(lines)

    for line in lines:
        if len(questions) >= max_q:
            break
        if line in used:
            continue
        used.add(line)

        if ":" in line:
            key, value = line.split(":", 1)
            value_parts = value.split(",") if "," in value else value.split()
            options = random.sample(value_parts, min(3, len(value_parts)))
            answer = value_parts[0].strip()
            options.append(answer)
            random.shuffle(options)
            questions.append({
                "question": f"What is associated with '{key.strip()}'?",
                "options": list(set(options)),
                "answer": answer
            })
        elif "added" in line or "adopted" in line or "enforced" in line:
            words = line.split()
            date = [w for w in words if re.match(r"\d{4}|\d{1,2}\s\w+", w)]
            if date:
                options = [date[0], "1947", "1950", "1976"]
                random.shuffle(options)
                questions.append({
                    "question": f"When was this true? — "{line}"",
                    "options": options,
                    "answer": date[0]
                })

    return questions

@app.post("/upload")
async def upload_pdf(pdf: UploadFile = File(...)):
    try:
        file_bytes = await pdf.read()
        text = extract_text(file_bytes)
        questions = generate_rule_based_questions(text)
        return {"questions": questions}
    except Exception as e:
        return {"questions": [], "error": str(e)}
