import random
from pathlib import Path

from Jarvis.Chunking import chunk_md_file
from Jarvis.Chunking.utils import count_token_approx


def main() -> None:
    print("Hello from Jarvis!")
    chunks = chunk_md_file(Path(__file__).resolve().parent / "LEARN.md")
    for i, c in enumerate(chunks):
        print(i, c.section[:50], count_token_approx(c.text), c.from_token_cut)
    print('\n#34 Chunk to read manually: ')
    print(chunks[34])
    print('\n #35 Chunk to read manually: ')
    print(chunks[35])


if __name__ == "__main__":
    main()
