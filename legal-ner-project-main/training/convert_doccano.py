import json, argparse, spacy
from spacy.tokens import DocBin

def convert(jsonl_path, out_path):
    nlp = spacy.blank("en")
    db = DocBin()
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            text = rec["text"]
            ents = rec.get("label") or rec.get("labels") or []
            doc = nlp.make_doc(text)
            spans=[]
            for item in ents:
                # Doccano can be [start, end, label] or dict
                if isinstance(item, list) and len(item) >= 3:
                    s,e,l = item[0], item[1], item[2]
                else:
                    s,e,l = item["start_offset"], item["end_offset"], item["label"]
                span = doc.char_span(s,e,label=l)
                if span: spans.append(span)
            doc.ents = spans
            db.add(doc)
    db.to_disk(out_path)
    print(f"✅ Saved spaCy DocBin to {out_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_jsonl", required=True)
    ap.add_argument("--out_spacy", default="train.spacy")
    args = ap.parse_args()
    convert(args.in_jsonl, args.out_spacy)
