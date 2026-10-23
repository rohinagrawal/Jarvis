import re
from dataclasses import dataclass

from Jarvis.Chunking.constants import TOKEN_LIMIT, OVERLAP_TOKEN, FLOOR_TOKEN_LIMIT
from Jarvis.Chunking.utils import file_reader, count_token_approx

@dataclass
class Chunk_MD:
    text: str
    section: str
    from_token_cut: bool

def chunk_md_file(path):
    chunks = []
    for section in _split_by_md_header(file_reader(path)):
        if count_token_approx(section.text) > TOKEN_LIMIT:
            chunks.extend(_split_oversized(section))
        else:
            chunks.append(section)
    return chunks

def _split_by_md_header(text: str):
    chunks = []
    for section in re.split(r"(?m)^(?=## )", text):
        if not section.strip():
            continue
        heading = section.strip().split("\n", 1)[0]
        chunks.append(Chunk_MD(section.strip(), heading, False))
    return chunks

def _split_oversized(chunk: Chunk_MD):
    # The heading is prepended to every chunk, so it counts against TOKEN_LIMIT
    # and is split off the body here to avoid repeating it in the first chunk.
    heading = chunk.section
    body = chunk.text.partition("\n")[2]
    budget = TOKEN_LIMIT - count_token_approx(heading)
    chunks = []
    buffer = []          # paragraphs waiting to become one chunk
    buffer_tokens = 0

    def flush():
        nonlocal buffer, buffer_tokens
        if buffer:
            chunks.append(Chunk_MD(heading + "\n\n" + "\n\n".join(buffer), heading, False))
        buffer = []
        buffer_tokens = 0

    for paragraph in body.split("\n\n"):
        if not paragraph.strip():
            continue
        tokens = count_token_approx(paragraph)
        if tokens > budget:
            flush()
            chunks.extend(_split_oversized_paragraph(Chunk_MD(paragraph, heading, True), budget))
        elif buffer_tokens + tokens > budget:
            flush()
            buffer.append(paragraph)
            buffer_tokens = tokens
        else:
            buffer.append(paragraph)
            buffer_tokens += tokens
    flush()
    return chunks

def _split_oversized_paragraph(chunk: Chunk_MD, budget: int):
    heading = chunk.section
    chunks = []
    words = chunk.text.split()
    step = budget - OVERLAP_TOKEN
    start = 0
    while True:
        piece = words[start:start + budget]
        if len(piece) - OVERLAP_TOKEN <= FLOOR_TOKEN_LIMIT:
            # Merge only the new words into the earlier chunk (heading already there)
            last_chunk: Chunk_MD = chunks.pop(-1)
            chunks.append(Chunk_MD(last_chunk.text + ' ' + " ".join(piece[OVERLAP_TOKEN:]), heading, True))
        else:
            chunks.append(Chunk_MD(heading + "\n\n" + " ".join(piece), heading, True))
        if start + budget >= len(words):
            break
        start += step
    return chunks
