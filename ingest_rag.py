"""Index the Markdown knowledge base in a local persistent Chroma collection."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import chromadb

from engine import (
    CHROMA_COLLECTION,
    CHROMA_PATH,
    KNOWLEDGE_BASE_DIR,
    OllamaEmbeddingFunction,
)


MAX_CHUNK_CHARS = 1400
CHUNK_OVERLAP_CHARS = 180
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)(?:\s+[^)]*)?\)")


def _read_markdown_sources(content: str) -> list[dict[str, str]]:
    lines = content.splitlines()
    source_start = None
    for index, line in enumerate(lines):
        if re.match(r"^#{1,3}\s+Public sources(?:\s|$)", line, re.IGNORECASE):
            source_start = index + 1
            break
    source_text = "\n".join(lines[source_start:]) if source_start is not None else content

    sources = []
    seen_urls = set()
    for title, url in MARKDOWN_LINK.findall(source_text):
        if url not in seen_urls:
            sources.append({"title": title.strip(), "url": url.strip()})
            seen_urls.add(url)
    return sources


def _section_for_position(content: str, position: int) -> str:
    section = "document"
    for match in re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", content):
        if match.start() > position:
            break
        section = match.group(1).strip()
    return section


def _split_long_paragraph(paragraph: str) -> list[str]:
    pieces = []
    start = 0
    while start < len(paragraph):
        end = min(start + MAX_CHUNK_CHARS, len(paragraph))
        if end < len(paragraph):
            boundary = paragraph.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        pieces.append(paragraph[start:end].strip())
        if end >= len(paragraph):
            break
        next_start = max(start + 1, end - CHUNK_OVERLAP_CHARS)
        next_space = paragraph.find(" ", next_start, end)
        start = next_space + 1 if next_space >= 0 else next_start
    return [piece for piece in pieces if piece]


def _markdown_chunks(content: str) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    buffer = ""
    buffer_position = 0
    cursor = 0

    for paragraph in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", content, re.DOTALL):
        text = paragraph.group(0).strip()
        if not text:
            continue
        if len(text) > MAX_CHUNK_CHARS:
            if buffer:
                chunks.append(
                    {
                        "text": buffer,
                        "section": _section_for_position(content, buffer_position),
                    }
                )
                buffer = ""
            for piece in _split_long_paragraph(text):
                chunks.append(
                    {
                        "text": piece,
                        "section": _section_for_position(content, paragraph.start()),
                    }
                )
        elif not buffer:
            buffer = text
            buffer_position = paragraph.start()
        elif len(buffer) + len(text) + 2 <= MAX_CHUNK_CHARS:
            buffer += "\n\n" + text
        else:
            chunks.append(
                {
                    "text": buffer,
                    "section": _section_for_position(content, buffer_position),
                }
            )
            tail = buffer[-CHUNK_OVERLAP_CHARS:].strip()
            first_space = tail.find(" ")
            if first_space >= 0:
                tail = tail[first_space + 1 :]
            buffer = f"{tail}\n\n{text}" if tail else text
            buffer_position = max(cursor, paragraph.start() - len(tail))
        cursor = paragraph.end()

    if buffer:
        chunks.append(
            {
                "text": buffer,
                "section": _section_for_position(content, buffer_position),
            }
        )
    return chunks


def _documents_from_knowledge_base() -> list[dict[str, Any]]:
    knowledge_base = Path(KNOWLEDGE_BASE_DIR)
    if not knowledge_base.is_dir():
        raise FileNotFoundError(f"Knowledge-base directory not found: {knowledge_base}")

    documents = []
    for path in sorted(knowledge_base.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        citations = _read_markdown_sources(content)
        relative_path = path.relative_to(knowledge_base.parent).as_posix()
        for index, chunk in enumerate(_markdown_chunks(content)):
            documents.append(
                {
                    "id": f"{relative_path}::{index}",
                    "text": chunk["text"],
                    "metadata": {
                        "source_file": relative_path,
                        "section": chunk["section"],
                        "chunk_index": index,
                        "citations_json": json.dumps(
                            citations, ensure_ascii=False
                        ),
                    },
                }
            )
    if not documents:
        raise FileNotFoundError(f"No Markdown files found in {knowledge_base}")
    return documents


def ingest(embedding_function: OllamaEmbeddingFunction | None = None) -> int:
    documents = _documents_from_knowledge_base()
    embedder = embedding_function or OllamaEmbeddingFunction()
    embeddings = embedder([item["text"] for item in documents])
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )
    existing_dimension = (collection.metadata or {}).get("embedding_dimension")
    if existing_dimension is None and collection.count():
        existing = collection.get(limit=1, include=["embeddings"])
        existing_embeddings = existing.get("embeddings")
        if existing_embeddings is not None and len(existing_embeddings):
            existing_dimension = len(existing_embeddings[0])
    if existing_dimension is not None and existing_dimension != len(embeddings[0]):
        client.delete_collection(name=CHROMA_COLLECTION)
        collection = client.create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

    collection.upsert(
        ids=[item["id"] for item in documents],
        documents=[item["text"] for item in documents],
        metadatas=[item["metadata"] for item in documents],
        embeddings=embeddings,
    )
    collection_metadata = dict(collection.metadata or {})
    collection_metadata.pop("hnsw:space", None)
    collection_metadata.update(
        {
            "embedding_backend": embedder.last_backend or "unknown",
            "embedding_dimension": len(embeddings[0]),
        }
    )
    collection.modify(metadata=collection_metadata)

    expected_ids = {item["id"] for item in documents}
    existing_ids = collection.get(include=[])["ids"]
    stale_ids = [identifier for identifier in existing_ids if identifier not in expected_ids]
    if stale_ids:
        collection.delete(ids=stale_ids)

    print(
        f"Indexed {len(documents)} chunks from "
        f"{len({item['metadata']['source_file'] for item in documents})} Markdown files "
        f"into Chroma collection '{CHROMA_COLLECTION}' at {CHROMA_PATH}."
    )
    return len(documents)


if __name__ == "__main__":
    ingest()
