import os

from dotenv import load_dotenv
from google import genai
from openai import OpenAI

load_dotenv("dev.env")


def main() -> None:
    print("Hello from Jarvis!")
    gemini()


def gemini():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Say hi in one word."
    )
    print(response.text)


# GitHub Models retired July 30, 2026 — this no longer works, kept for reference only
def github():
    client = OpenAI(
        base_url="https://models.github.ai/inference",
        api_key=os.environ["GITHUB_TOKEN"],
    )
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hi in one word."}],
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
