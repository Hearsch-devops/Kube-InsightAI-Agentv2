from pathlib import Path


DOCUMENTS_DIR = Path(__file__).parent.parent / "knowledge_base" / "kubernetes"


def load_documents():
    documents = []

    for file_path in DOCUMENTS_DIR.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")

        documents.append({
            "source": str(file_path),
            "content": content
        })

    return documents


if __name__ == "__main__":
    documents = load_documents()

    print(f"Loaded {len(documents)} documents")

    for document in documents:
        print("--------------------------------")
        print(f"Source: {document['source']}")
        print(f"Characters: {len(document['content'])}")
