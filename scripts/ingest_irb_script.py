"""
Usage: python scripts/ingest_irb_script.py --file path/to/irb_script.txt --study-id STUDY-001
"""
import argparse
import sys
sys.path.insert(0, ".")

from src.db.session import get_db
from src.rag.knowledge_base import KnowledgeBase


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--study-id", required=True)
    args = parser.parse_args()

    db = next(get_db())
    kb = KnowledgeBase(db_session=db)

    with open(args.file) as f:
        content = f.read()

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    for i, para in enumerate(paragraphs):
        kb.add_entry(
            key=f"{args.study_id}-segment-{i}",
            content=para,
            tags=["irb_approved", args.study_id],
            study_id=args.study_id,
        )
        print(f"Ingested segment {i+1}/{len(paragraphs)}")

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
