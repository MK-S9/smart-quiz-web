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
    return any(x in line.lower() for x in [":", "-", "→", "->", "—", "=", "types", "adopted", "added", "date", "case", "schedule"])

def clean_line(line):
    line = line.strip()
    line = re.sub(r"[•*●▪️■◆]", "", line)  # remove bullets
    line = re.sub(r"[^a-zA-Z0-9:.,\\-\\s]", "", line)  # remove special junk
    return line.strip()

def generate_rule_based_questions(text, max_q=10):
    lines = [clean_line(l) for l in text.splitlines() if len(l.strip()) > 15 and is_fact_line(l)]
    used = set()
    questions = []
    random.shuffle(lines)

    for line in lines:
        if len(questions) >= max_q:
            break
        if line in used or len(line.split()) < 4:
            continue
        used.add(line)

        if ":" in line:
            key, value = line.split(":", 1)
            value_words = value.split()
            if len(value_words) < 2 or len(key.split()) < 1:
                continue
            answer = value_words[0].strip()
            distractors = random.sample(value_words[1:], min(3, len(value_words[1:]))) if len(value_words) > 3 else ["Justice", "Liberty", "Equality"]
            options = list(set([answer] + distractors))
            random.shuffle(options)
            questions.append({
                "question": f"What is associated with \"{key.strip()}\"?",
                "options": options,
                "answer": answer
            })
        elif any(word in line.lower() for word in ["added", "adopted", "enforced"]):
            words = line.split()
            date = next((w for w in words if re.match(r"\\d{4}", w)), None)
            if date:
                options = list(set([date, "1947", "1950", "1976"]))
                random.shuffle(options)
                questions.append({
                    "question": f"When was this true? — \"{line}\"",
                    "options": options,
                    "answer": date
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
