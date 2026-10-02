import os
import json
import uuid

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app.extraction import extract_invoice
from app.po_extraction import extract_po
from app.database import get_purchase_order
from app.matching import match_invoice_to_po
from app.validation import validate_document_financials
from app.agents import explain_exception
from app.routing import determine_route
from app.storage import (
    init_db,
    invoice_exists,
    save_invoice,
    log_event,
    save_human_decision,
    reset_test_data
)

from pydantic import BaseModel


class ReviewDecision(BaseModel):
    decision: str
    reviewer: str = "demo-user"
    notes: str = ""


app = FastAPI(
    title="Invoice Agent Prototype"
)

init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_DIR = "uploads"

DEVELOPMENT_MODE = (
    os.getenv(
        "DEVELOPMENT_MODE",
        "false"
    ).lower()
    == "true"
)

os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def root():
    return {
        "message": "Invoice Agent is running"
    }



@app.post("/review/{invoice_id}")
def review_invoice(
    invoice_id: str,
    review: ReviewDecision
):
    save_human_decision(
        invoice_id,
        review.decision,
        review.reviewer,
        review.notes
    )

    log_event(
        invoice_id,
        "HUMAN_REVIEW_COMPLETED",
        {
            "decision": review.decision,
            "reviewer": review.reviewer,
            "notes": review.notes
        }
    )

    return {
        "invoice_id": invoice_id,
        "status": "saved",
        "decision": review.decision
    }


@app.post("/process-documents")
async def process_documents(
    invoice_file: UploadFile = File(...),
    po_file: UploadFile = File(...)
):

    invoice_id = str(uuid.uuid4())

    # ----------------------------
    # Save invoice
    # ----------------------------

    invoice_extension = os.path.splitext(
        invoice_file.filename
    )[1]

    invoice_path = os.path.join(
        UPLOAD_DIR,
        f"{invoice_id}_invoice{invoice_extension}"
    )

    with open(invoice_path, "wb") as f:
        f.write(await invoice_file.read())


    # ----------------------------
    # Save PO
    # ----------------------------

    po_extension = os.path.splitext(
        po_file.filename
    )[1]

    po_path = os.path.join(
        UPLOAD_DIR,
        f"{invoice_id}_po{po_extension}"
    )

    with open(po_path, "wb") as f:
        f.write(await po_file.read())


    # ----------------------------
    # Audit event
    # ----------------------------

    log_event(
        invoice_id,
        "DOCUMENTS_RECEIVED",
        {
            "invoice_filename": invoice_file.filename,
            "po_filename": po_file.filename
        }
    )


    # ----------------------------
    # Extract invoice
    # ----------------------------

    invoice_result = extract_invoice(
            invoice_path
        )


    # ----------------------------
    # Extract PO
    # ----------------------------

    po_result = extract_po(
            po_path
        )


    # ----------------------------
    # Schema / extraction validation
    # ----------------------------

    extraction_errors = []

    if not invoice_result["success"]:
        extraction_errors.append(
            invoice_result["error"]
        )

    if not po_result["success"]:
        extraction_errors.append(
            po_result["error"]
        )


    if extraction_errors:

        matching_result = {
            "decision": "EXCEPTION",
            "reason": "EXTRACTION_VALIDATION_FAILURE",
            "exceptions": extraction_errors,
            "line_item_matching": []
        }

        log_event(
            invoice_id,
            "EXTRACTION_VALIDATION_FAILED",
            {
                "errors": extraction_errors
            }
        )

        route = determine_route(
            extraction_errors
        )

        log_event(
            invoice_id,
            "ROUTED_FOR_REVIEW",
            {
                "route": route
            }
        )

        return {
            "invoice_id": invoice_id,

            "invoice": {},

            "invoice_confidence": {},

            "purchase_order": {},

            "po_confidence": {},

            "matching": matching_result,

            "route": route,

            "exception_analysis": {
                "summary": "Document extraction validation failed.",
                "severity": "High",
                "recommended_action": (
                    "Review the source document and extracted fields "
                    "before continuing with invoice matching."
                )
            }
        }


    # ----------------------------
    # Use validated extraction data
    # ----------------------------

    invoice_extracted = invoice_result["data"]
    po_extracted = po_result["data"]

    invoice = invoice_extracted["invoice"]

    invoice_confidence = (
        invoice_extracted["confidence"]
    )

    po = po_extracted["purchase_order"]

    po_confidence = (
        po_extracted["confidence"]
    )



    log_event(
        invoice_id,
        "DOCUMENTS_EXTRACTED",
        {
            "invoice": invoice,
            "invoice_confidence": invoice_confidence,
            "purchase_order": po,
            "po_confidence": po_confidence
        }
    )



    # ----------------------------
    # Financial sanity validation
    # ----------------------------

    financial_exceptions = []

    financial_exceptions.extend(
        validate_document_financials(
            invoice,
            "invoice"
        )
    )

    financial_exceptions.extend(
        validate_document_financials(
            po,
            "purchase_order"
        )
    )


    log_event(
        invoice_id,
        "FINANCIAL_VALIDATION_COMPLETED",
        {
            "exceptions": financial_exceptions
        }
    )


    # ----------------------------
    # Duplicate check
    # ----------------------------

    is_duplicate = invoice_exists(
        invoice["vendor"],
        invoice["invoice_number"]
    )


    # ----------------------------
    # Confidence checks
    # ----------------------------

    LOW_CONFIDENCE_THRESHOLD = 0.95

    low_confidence_fields = []


    for field, score in invoice_confidence.items():

        if score < LOW_CONFIDENCE_THRESHOLD:

            low_confidence_fields.append({
                "document": "invoice",
                "field": field,
                "confidence": score
            })


    for field, score in po_confidence.items():

        if score < LOW_CONFIDENCE_THRESHOLD:

            low_confidence_fields.append({
                "document": "purchase_order",
                "field": field,
                "confidence": score
            })


    # ----------------------------
    # Decision
    # ----------------------------

    if is_duplicate:

        matching_result = {
            "decision": "EXCEPTION",
            "reason": "DUPLICATE_INVOICE",
            "exceptions": [
                {
                    "type": "DUPLICATE_INVOICE",
                    "message": (
                        "This vendor and invoice number "
                        "have already been processed."
                    )
                }
            ]
        }

    elif financial_exceptions:

        matching_result = {
            "decision": "EXCEPTION",
            "reason": "FINANCIAL_VALIDATION_FAILURE",
            "exceptions": financial_exceptions,
            "line_item_matching": []
        }


    elif low_confidence_fields:

        matching_result = {
            "decision": "EXCEPTION",
            "reason": "LOW_EXTRACTION_CONFIDENCE",
            "exceptions": [
                {
                    "type": "LOW_CONFIDENCE",
                    "message": (
                        f"{item['document']} field "
                        f"{item['field']} has confidence "
                        f"{item['confidence']:.2f}"
                    )
                }
                for item in low_confidence_fields
            ]
        }


    else:

        matching_result = match_invoice_to_po(
            invoice,
            po
        )


    # ----------------------------
    # Audit match
    # ----------------------------

    log_event(
        invoice_id,
        "MATCH_COMPLETED",
        matching_result
    )


    # ----------------------------
    # Routing
    # ----------------------------

    route = None

    if matching_result["decision"] == "EXCEPTION":

        route = determine_route(
            matching_result["exceptions"]
        )

        log_event(
            invoice_id,
            "ROUTED_FOR_REVIEW",
            {
                "route": route
            }
        )


    # ----------------------------
    # AI explanation
    # ----------------------------

    explanation = None

    if matching_result["decision"] == "EXCEPTION":

        explanation = explain_exception(
            invoice,
            po,
            matching_result
        )


    # ----------------------------
    # Save record
    # ----------------------------

    save_invoice(
        invoice_id,
        invoice,
        matching_result["decision"]
    )


    # ----------------------------
    # Response
    # ----------------------------

    return {
        "invoice_id": invoice_id,

        "invoice": invoice,

        "invoice_confidence": invoice_confidence,

        "purchase_order": po,

        "po_confidence": po_confidence,

        "matching": matching_result,

        "route": route,

        "exception_analysis": explanation
    }


@app.post("/dev/reset-test-data")
def reset_prototype_data():

    if not DEVELOPMENT_MODE:

        return {
            "success": False,
            "message": (
                "Reset endpoint is disabled "
                "outside development mode."
            )
        }

    reset_test_data()

    return {
        "success": True,
        "message": "Test data cleared successfully."
    }

@app.get("/config")
def get_config():
    return {
        "development_mode": DEVELOPMENT_MODE
    }