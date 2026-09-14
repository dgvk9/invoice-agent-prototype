
import os
import json
import fitz

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_text_from_pdf(file_path):
    document = fitz.open(file_path)

    text = ""

    for page in document:
        text += page.get_text()

    return text


def extract_invoice(file_path):

    invoice_text = extract_text_from_pdf(file_path)

    prompt = f"""
You are an invoice extraction agent.

Extract the invoice information from the document below.

Return ONLY valid JSON.

Required structure:

{{
  "invoice": {{
    "vendor": "",
    "invoice_number": "",
    "invoice_date": "",
    "po_number": "",
    "currency": "",
    "subtotal": 0,
    "tax": 0,
    "total": 0,
    "line_items": [
      {{
        "description": "",
        "quantity": 0,
        "unit_price": 0,
        "amount": 0
      }}
    ]
  }},
  "confidence": {{
    "vendor": 0.0,
    "invoice_number": 0.0,
    "po_number": 0.0,
    "total": 0.0
  }}
}}

Rules:

- Do not invent information.
- If information is unavailable, use null.
- Numbers must be numbers, not strings.
- Extract every relevant line item.
- Preserve the invoice's currency.
- Confidence values must be numbers between 0 and 1.
- Use lower confidence when a field is unclear, ambiguous, or difficult to read.
- Do not assign high confidence to inferred values.
- A confidence of 1.0 means the field is clearly and unambiguously present.
- A confidence near 0 means the field cannot be reliably determined.

Invoice:

{invoice_text} 

"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt
    )

    result = response.output_text

    return json.loads(result)
