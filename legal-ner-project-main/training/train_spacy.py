import os, re, random, argparse, spacy
from spacy.tokens import DocBin
from spacy.training.example import Example
import fitz  # PyMuPDF

DATE_RE = re.compile(r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b")
SECTION_RE = re.compile(r"(?i)\bsec(?:tion)?\.?\s*\d+[A-Z]?(?:\([\w\d]+\))*")
COURT_RE = re.compile(r"(?i)\b(?:Supreme Court|[A-Za-z]+ High Court|District Court|Sessions Court)\b")

def extract_text(pdf_path):
    text=[]
    with fitz.open(pdf_path) as doc:
        for p in doc:
            text.append(p.get_text())
    return "\n".join(text)

def auto_annotate(text):
    ents=[]
    for m in DATE_RE.finditer(text): ents.append((m.start(), m.end(), "DATE"))
    for m in SECTION_RE.finditer(text): ents.append((m.start(), m.end(), "SECTION"))
    for m in COURT_RE.finditer(text): ents.append((m.start(), m.end(), "COURT"))
    ents.sort(key=lambda x:(x[0],-(x[1]-x[0])))
    out=[]; last=-1
    for s,e,l in ents:
        if s>=last:
            out.append((s,e,l)); last=e
    return out

def build_docbin(pdf_dir, out_path):
    nlp = spacy.blank("en")
    db = DocBin()
    for fn in os.listdir(pdf_dir):
        if fn.lower().endswith(".pdf"):
            text = extract_text(os.path.join(pdf_dir, fn))
            anns = auto_annotate(text)
            doc = nlp.make_doc(text)
            spans=[]
            for s,e,l in anns:
                span = doc.char_span(s,e,label=l)
                if span: spans.append(span)
            doc.ents = spans
            db.add(doc)
    db.to_disk(out_path)

def train(train_spacy_path, out_dir, n_iter=20):
    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")
    for label in ["DATE","SECTION","COURT"]:
        ner.add_label(label)
    db = DocBin().from_disk(train_spacy_path)
    docs = list(db.get_docs(nlp.vocab))
    examples=[]
    for d in docs:
        ents=[(e.start_char, e.end_char, e.label_) for e in d.ents]
        examples.append(Example.from_dict(d, {"entities": ents}))
    optimizer = nlp.begin_training()
    for i in range(n_iter):
        random.shuffle(examples)
        losses={}
        for batch in spacy.util.minibatch(examples, size=4):
            nlp.update(batch, drop=0.2, sgd=optimizer, losses=losses)
        print(f"Epoch {i+1}/{n_iter} - Losses {losses}")
    os.makedirs(out_dir, exist_ok=True)
    nlp.to_disk(out_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", type=str, required=True, help="Folder with PDFs")
    parser.add_argument("--train_path", type=str, default="train.spacy")
    parser.add_argument("--out", type=str, default="../models/legal_ner_model")
    parser.add_argument("--epochs", type=int, default=20)
    args = parser.parse_args()

    build_docbin(args.pdf_dir, args.train_path)
    train(args.train_path, args.out, args.epochs)
    print(f"✅ Trained model saved to {args.out}")
