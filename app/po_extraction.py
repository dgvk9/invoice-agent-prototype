import os
import json

from openai import OpenAI
from dotenv import load_dotenv

from app.document_input import build_document_content


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def extract_po(file_path):

    instructions = """
You are a purchase order extraction agent.

Extract information from the purchase order.

Return ONLY valid JSON.

Required structure:

{
  "purchase_order": {
    "po_number": "",
    "vendor": "",
    "po_date": "",
    "currency": "",
    "category": "",
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
    "po_number": 0.0,
    "vendor": 0.0,
    "currency": 0.0,
    "total": 0.0
  }
}

Rules:

- Do not invent information.
- If information is unavailable, use null.
- Numbers must be numbers, not strings.
- Extract all relevant line items.
- Preserve the document currency.
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