import re


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def split_large_section(
    section,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
):
    chunks = []

    start = 0

    while start < len(section):

        end = start + chunk_size

        chunk = section[start:end]

        chunks.append(chunk)

        start += chunk_size - chunk_overlap

    return chunks


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

        section = "# " + section

        if len(section) <= CHUNK_SIZE:

            chunks.append(section)

        else:

            chunks.extend(
                split_large_section(section)
            )

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
                    "chunk_type": "hybrid"
                }
            })

    return chunks


if __name__ == "__main__":

    from .document_loader import load_documents

    documents = load_documents()

    chunks = split_documents(documents)

    sizes = [
        len(chunk["content"])
        for chunk in chunks
    ]

    print(f"Documents: {len(documents)}")
    print(f"Generated chunks: {len(chunks)}")
    print(
        f"Smallest chunk: {min(sizes)} characters"
    )
    print(
        f"Largest chunk: {max(sizes)} characters"
    )
    print(
        f"Average chunk: "
        f"{sum(sizes) / len(sizes):.0f} characters"
    )
