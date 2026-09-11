import re


def split_markdown_sections(text):

    sections = re.split(
        r"(?m)^# ",
        text
    )

    chunks = []

    for section in sections:

        section = section.strip()

        if not section:
            continue

        chunks.append("# " + section)

    return chunks


def split_documents(documents):

    chunks = []

    for document in documents:

        sections = split_markdown_sections(
            document["content"]
        )

        for index, section in enumerate(sections):

            chunks.append({
                "content": section,
                "metadata": {
                    "source": document["source"],
                    "chunk_index": index,
                    "chunk_type": "markdown_section"
                }
            })

    return chunks


if __name__ == "__main__":

    from document_loader import load_documents

    documents = load_documents()

    chunks = split_documents(documents)

    print(f"Documents: {len(documents)}")
    print(f"Generated sections: {len(chunks)}")

    sizes = [
        len(chunk["content"])
        for chunk in chunks
    ]

    print(f"Smallest section: {min(sizes)} characters")
    print(f"Largest section: {max(sizes)} characters")
    print(
        f"Average section: "
        f"{sum(sizes) / len(sizes):.0f} characters"
    )

    print("\nLargest sections:")

    largest = sorted(
        chunks,
        key=lambda chunk: len(chunk["content"]),
        reverse=True
    )

    for chunk in largest[:10]:

        print("\n--------------------------------")
        print(
            f"Source: "
            f"{chunk['metadata']['source']}"
        )
        print(
            f"Section: "
            f"{chunk['metadata']['chunk_index']}"
        )
        print(
            f"Characters: "
            f"{len(chunk['content'])}"
        )
        print(
            f"Preview:\n"
            f"{chunk['content'][:300]}"
        )
