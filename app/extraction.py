import os
import json

from openai import OpenAI
from dotenv import load_dotenv

from app.document_input import build_document_content


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def extract_invoice(file_path):

    instructions = """
You are an invoice extraction agent.

Extract information from the invoice.

Return ONLY valid JSON.

Required structure:

{
  "invoice": {
    "vendor": "",
    "invoice_number": "",
    "invoice_date": "",
    "po_number": "",
    "currency": "",
    "subtotal": 0,
    "tax": 0,
    "total": 0,
    "line_items": [
      {
        "description": "",
        "quantity": 0,
        "unit_price": 0,
        "amount": 0
      }
    ]
  },

  "confidence": {
    "vendor": 0.0,
    "invoice_number": 0.0,
    "po_number": 0.0,
    "total": 0.0
  }
}

Rules:

- Do not invent information.
- If information is unavailable, use null.
- Numbers must be numbers, not strings.
- Extract all relevant line items.
- Preserve the invoice currency.
- Confidence must be between 0 and 1.
- Lower confidence when text is unclear or ambiguous.
- Do not give high confidence to inferred values.
"""

    content = build_document_content(
        file_path,
        instructions
    )

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=[
            {
                "role": "user",
                "content": content
            }
        ]
    )

    return json.loads(
        response.output_text
    )