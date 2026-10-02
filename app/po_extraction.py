import os
import json

from openai import OpenAI
from dotenv import load_dotenv

from app.document_input import build_document_content
from pydantic import ValidationError
from app.models import POExtraction


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
    "subtotal": null,
    "tax": null,
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
    "subtotal": 0.0,
    "tax": 0.0,
    "total": 0.0,
    "line_items": 0.0
  }
}

Rules:
- Do not invent information.
- If information is unavailable, use null.
- Numbers must be numbers, not strings.
- Extract every purchase order line item individually.
- Do not combine separate line items into one line.
- Preserve the document currency.
- Extract subtotal before tax when explicitly available.
- Extract the tax amount separately when explicitly available.
- If tax is explicitly shown as zero, return 0.
- If tax is not stated, return null.
- Do not infer tax solely by subtracting subtotal from total.
- For each line item, extract description, quantity, unit price and amount.
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

    try:
        raw_result = json.loads(response.output_text)

        validated_result = POExtraction.model_validate(
            raw_result
        )

        return {
            "success": True,
            "data": validated_result.model_dump()
        }

    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "error": {
                "type": "EXTRACTION_VALIDATION_ERROR",
                "document": "purchase_order",
                "message": "Purchase order extraction did not return valid JSON.",
                "details": str(exc)
            }
        }

    except ValidationError as exc:
        return {
            "success": False,
            "error": {
                "type": "EXTRACTION_VALIDATION_ERROR",
                "document": "purchase_order",
                "message": "Purchase order extraction did not match the required schema.",
                "details": exc.errors()
            }
        }