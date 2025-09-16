import spacy

# Global variable for loading model only once
_nlp = None

def ensure_nlp():
    """
    Load spaCy pretrained model once and reuse.
    """
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")   # ✅ Pretrained NER model
            print("✅ spaCy model loaded successfully.")
        except OSError:
            raise RuntimeError(
                "❌ spaCy model 'en_core_web_sm' not found. "
                "Run this command first: python -m spacy download en_core_web_sm"
            )
    return _nlp


def run_ner(text: str):
    """
    Run Named Entity Recognition on input text.
    Returns entities with text, label, start, end, score.
    """
    nlp = ensure_nlp()
    doc = nlp(text)

    entities = []
    for ent in doc.ents:
        entities.append({
            "text": ent.text,
            "label": ent.label_,        # PERSON, ORG, GPE, DATE, MONEY, LAW, etc.
            "start": ent.start_char,
            "end": ent.end_char,
            "score": 1.0                # spaCy doesn’t provide score, so default 1.0
        })

    return entities


# ✅ Test Run
if __name__ == "__main__":
    sample_text = "On 18 September 1982, the Supreme Court fined Mr. Sharma ₹5,00,000 in Delhi under Section 302."
    ents = run_ner(sample_text)
    print("Extracted Entities:")
    for e in ents:
        print(e)
