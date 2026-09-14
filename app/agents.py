import os
import json

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def explain_exception(invoice, po, matching_result):

    prompt = f"""
You are an accounts-payable exception analyst.

Analyze this invoice and purchase order.

INVOICE:
{invoice}

PURCHASE ORDER:
{po}

MATCHING RESULT:
{matching_result}

Write a concise explanation for an AP reviewer.

Return JSON:

{{
  "summary": "",
  "severity": "LOW | MEDIUM | HIGH",
  "recommended_action": ""
}}

Do not invent facts.
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt
    )

    return json.loads(response.output_text)
