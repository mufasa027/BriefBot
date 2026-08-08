from openai import OpenAI
from settings import OPENROUTER_API_KEY
import json
import re

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

SYSTEM_PROMPT = """
You are BriefBot's AI news analyst.

Analyze the article and return ONLY valid JSON.

{
    "summary":"80-120 word summary",
    "category":"Politics",
    "keywords":["","","","",""],
    "importance":1,
    "confidence":95,
    "sentiment":"Neutral",
    "region":"Global",
    "people":[""],
    "organizations":[""],
    "countries":[""],
    "topics":[""]
}
"""


def summarize_article(article):

    response = client.chat.completions.create(
        model="deepseek/deepseek-chat-v3.1",
        temperature=0.2,
        max_tokens=350,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"""
Title:
{article["title"]}

Article:
{article["summary"]}
"""
            }
        ],
    )

    result = response.choices[0].message.content.strip()
    result = re.sub(r"```json|```", "", result).strip()

    try:
        data = json.loads(result)
    except Exception:
        article["category"] = "World"
        article["keywords"] = ""
        article["importance"] = 5
        article["confidence"] = 50
        article["sentiment"] = "Neutral"
        article["region"] = "Global"
        article["people"] = ""
        article["organizations"] = ""
        article["countries"] = ""
        article["topics"] = ""
        return article

    article["summary"] = data.get("summary", article["summary"])
    article["category"] = data.get("category", "World")
    article["keywords"] = ", ".join(data.get("keywords", []))
    article["importance"] = data.get("importance", 5)
    article["confidence"] = data.get("confidence", 50)
    article["sentiment"] = data.get("sentiment", "Neutral")
    article["region"] = data.get("region", "Global")
    article["people"] = ", ".join(data.get("people", []))
    article["organizations"] = ", ".join(data.get("organizations", []))
    article["countries"] = ", ".join(data.get("countries", []))
    article["topics"] = ", ".join(data.get("topics", []))

    return article
