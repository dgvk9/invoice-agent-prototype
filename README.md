# Invoice Agent Prototype

A human-in-the-loop accounts-payable prototype that extracts data from
invoices and purchase orders, performs deterministic matching,
classifies and routes exceptions, and records human review decisions.

> **Design principle:** AI handles document interpretation and
> reviewer-facing explanations. Deterministic Python rules handle
> financial matching and routing. Humans make final decisions on
> exceptions.

## What it does

The prototype supports an end-to-end workflow:

``` text
Invoice PDF/Image       Purchase Order PDF/Image
       |                         |
       v                         v
Invoice Extraction       PO Extraction
       |                         |
       +-----------+-------------+
                   |
                   v
            Normalized Data
                   |
                   v
      Duplicate + Confidence Checks
                   |
                   v
        Deterministic Matching
                   |
          +--------+--------+
          |                 |
          v                 v
        MATCH           EXCEPTION
                            |
                            v
                    Exception Routing
                            |
                            v
                    AI Explanation
                            |
                            v
                     Human Review
                    Approve / Reject
                            |
                            v
                        Audit Log
```

## Key features

-   Invoice extraction from PDF and image documents
-   Purchase-order extraction from PDF and image documents
-   Structured JSON normalization
-   Field-level extraction confidence for important fields
-   Duplicate invoice detection
-   Deterministic invoice-to-PO matching
-   Structured exception classification
-   Exception routing to functions such as Procurement, Receiving, and
    Accounts Payable
-   AI-generated exception explanations for reviewers
-   Human approve/reject workflow
-   SQLite persistence and audit logging
-   Development-only test-data reset
-   Simple browser-based frontend
-   FastAPI/Swagger API for backend testing

## AI agent responsibilities

### Invoice extraction agent

The invoice extraction agent converts unstructured invoice content into
structured fields such as:

-   vendor
-   invoice number
-   invoice date
-   PO number
-   currency
-   subtotal, tax, and total
-   line items
-   extraction confidence

### Purchase-order extraction agent

The PO extraction agent normalizes uploaded purchase orders into fields
such as:

-   PO number
-   vendor
-   PO date
-   currency
-   category
-   total
-   line items
-   extraction confidence

### Exception-analysis agent

When deterministic matching detects an exception, the exception-analysis
agent receives the invoice, PO, and matching result and produces a
concise reviewer-facing explanation.

The AI explanation is **not** the authoritative match decision. The
matching engine remains the source of truth for detected financial
discrepancies.

## Deterministic controls

The Python matching layer can identify exceptions such as:

  Exception                    Typical route
  ---------------------------- ------------------
  `PRICE_VARIANCE`             Procurement
  `QUANTITY_VARIANCE`          Receiving
  `MISSING_PO`                 Accounts Payable
  `PO_NUMBER_MISMATCH`         Accounts Payable
  `VENDOR_MISMATCH`            Accounts Payable
  `CURRENCY_MISMATCH`          Accounts Payable
  `TOTAL_MISMATCH`             Accounts Payable
  `LINE_ITEM_COUNT_MISMATCH`   Accounts Payable
  `DUPLICATE_INVOICE`          Accounts Payable
  `LOW_CONFIDENCE`             Accounts Payable

Routing rules are prototype business rules and can be changed for a real
pilot.

## Tech stack

-   **Python**
-   **FastAPI** --- backend API and workflow orchestration
-   **OpenAI API / GPT-5.6 Luna** --- document extraction and exception
    explanation
-   **PyMuPDF** --- PDF text extraction/rendering
-   **SQLite** --- prototype persistence, duplicate checks, human
    decisions, and audit data
-   **HTML/CSS/JavaScript** --- lightweight frontend
-   **Uvicorn** --- local ASGI server

## Project structure

A typical repository layout is:

``` text
invoice-agent/
├── app/
│   ├── main.py
│   ├── extraction.py
│   ├── po_extraction.py
│   ├── document_input.py
│   ├── matching.py
│   ├── routing.py
│   ├── agents.py
│   ├── storage.py
│   └── database.py
├── data/
│   └── synthetic test data / prototype PO data
├── frontend/
│   └── index.html
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Local runtime files such as `.env`, `invoice_agent.db`, `uploads/`, and
`venv/` should not be committed.

## Quick start

### 1. Clone the repository

``` bash
git clone https://github.com/dgvk9/invoice-agent-prototype
cd invoice-agent
```

### 2. Create a virtual environment

On macOS/Linux:

``` bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

If you do not yet have a `requirements.txt`, create one from the working
virtual environment before publishing the project:

``` bash
pip freeze > requirements.txt
```

### 4. Configure environment variables

Copy the example file:

``` bash
cp .env.example .env
```

Then edit `.env`:

``` text
OPENAI_API_KEY=your_api_key_here
DEVELOPMENT_MODE=true
```

Never commit your real `.env` or API key.

For a production-like environment, use:

``` text
DEVELOPMENT_MODE=false
```

### 5. Start the backend

From the project root:

``` bash
uvicorn app.main:app --reload
```

The backend should be available at:

``` text
http://127.0.0.1:8000
```

Swagger API documentation:

``` text
http://127.0.0.1:8000/docs
```

### 6. Start the frontend

Open another terminal, navigate to the frontend directory, and serve it
with a simple local web server:

``` bash
cd frontend
python3 -m http.server 5500
```

Then open:

``` text
http://127.0.0.1:5500
```

## API workflow

The prototype has evolved through two processing paths.

### `POST /process-invoice`

Original workflow:

1.  upload an invoice
2.  extract invoice data
3.  look up the PO from the prototype PO data source
4.  run duplicate/confidence checks
5.  perform matching
6.  route exceptions
7.  return the result

### `POST /process-documents`

Document-to-document workflow:

1.  upload an invoice PDF/image
2.  upload a PO PDF/image
3.  extract both documents
4.  normalize both records
5.  run duplicate/confidence checks
6.  compare invoice against PO
7.  classify and route exceptions
8.  generate an exception explanation when needed

### `POST /review/{invoice_id}`

Stores a human review decision such as:

``` json
{
  "decision": "REJECT",
  "reviewer": "demo-user",
  "notes": ""
}
```

### `POST /dev/reset-test-data`

Development-only endpoint that clears prototype test records.

This endpoint should only be usable when:

``` text
DEVELOPMENT_MODE=true
```

### `GET /config`

Allows the frontend to determine whether development-only UI features,
such as **Reset Test Data**, should be shown.

## Example scenarios

### Exact match

Invoice:

``` text
Vendor: Acme Software Inc.
PO: PO-1001
Quantity: 100
Unit price: USD 100
Total: USD 10,000
```

PO:

``` text
Vendor: Acme Software Inc.
PO: PO-1001
Quantity: 100
Unit price: USD 100
Total: USD 10,000
```

Expected result:

``` text
MATCH
```

### Price variance

Invoice unit price:

``` text
USD 120
```

PO unit price:

``` text
USD 100
```

Expected result includes:

``` text
EXCEPTION
PRICE_VARIANCE
Route: Procurement
```

Depending on the totals, a total mismatch may also be detected.

### Duplicate invoice

Process the same vendor/invoice-number combination twice.

The second processing attempt should produce:

``` text
EXCEPTION
DUPLICATE_INVOICE
Route: Accounts Payable
```

### Low extraction confidence

If a critical extracted field falls below the configured confidence
threshold, the prototype can route the invoice for human review instead
of trusting the extraction automatically.

> Model-reported confidence is a prototype heuristic, not a calibrated
> statistical probability.

## Human review

For exceptions, the frontend displays the detected issues, route, and
AI-generated explanation.

The reviewer can then select:

``` text
Approve
Reject
```

The frontend retains the current `invoice_id` and sends the decision to
the backend review endpoint. The decision is persisted in SQLite and can
be included in the audit trail.

## Audit trail

The prototype can record workflow events such as:

``` text
INVOICE_RECEIVED
INVOICE_EXTRACTED
DUPLICATE_CHECK
CONFIDENCE_CHECK
PO_LOOKUP
MATCH_COMPLETED
ROUTED_FOR_REVIEW
EXCEPTION_ANALYZED
INVOICE_SAVED
HUMAN_REVIEW_COMPLETED
```

This makes the workflow easier to inspect and debug and demonstrates the
traceability expected in an AP automation system.

## Development test reset

During local testing, repeatedly processing the same sample invoice will
intentionally trigger duplicate detection.

When:

``` text
DEVELOPMENT_MODE=true
```

the frontend can expose a **Reset Test Data** button that calls the
development reset endpoint and clears prototype records before the next
test case.

In production:

``` text
DEVELOPMENT_MODE=false
```

The reset control should be hidden and the backend must refuse reset
operations.

A real production financial system should not provide an equivalent
endpoint for deleting audit history.

## Security

Do not commit sensitive or runtime data.

Recommended `.gitignore` entries:

``` gitignore
# Secrets
.env
.env.*
!.env.example

# Virtual environments
venv/
.venv/

# Python
__pycache__/
*.pyc

# Local databases
*.db
*.sqlite
*.sqlite3

# Uploaded documents
uploads/

# macOS
.DS_Store

# IDEs
.vscode/
.idea/

# Logs
*.log
```

Before pushing, verify:

``` bash
git check-ignore .env
git check-ignore invoice_agent.db
git check-ignore uploads/
git status
```

Your real OpenAI API key must never appear in source code, README files,
Git history, screenshots, or sample configuration files.

## Test data

Use only synthetic/non-sensitive invoice and PO documents when
publishing sample files in the repository.

Useful test cases include:

1.  exact match
2.  price variance
3.  quantity variance
4.  currency mismatch
5.  vendor mismatch
6.  PO-number mismatch
7.  duplicate invoice
8.  low-confidence extraction

Do not publish real supplier invoices or purchase orders unless you have
appropriate authorization and have handled sensitive data requirements.

## Prototype limitations

This repository is a prototype, not a production accounts-payable
system.

Current prototype choices may include:

-   SQLite instead of an enterprise database
-   local file storage
-   simple frontend authentication assumptions
-   model-reported extraction confidence
-   simplified matching tolerances
-   simplified line-item matching
-   manually defined routing rules
-   synthetic PO/test data
-   development-only reset capabilities

## Production roadmap

A production implementation would typically add:

-   ERP/procurement-system integration
-   secure object storage
-   SSO and role-based access control
-   reviewer queues and assignments
-   configurable matching tolerances
-   receipt data and three-way matching
-   tax, freight, credit memo, and partial-invoice handling
-   schema-enforced extraction
-   calibrated extraction-quality metrics
-   model/evaluation monitoring
-   immutable audit controls
-   database migrations and backups
-   encryption and secrets management
-   document retention policies
-   observability and alerting
-   retry/idempotency handling

## Suggested pilot metrics

For a defined vendor-category pilot, measure:

-   extraction accuracy by field
-   straight-through match rate
-   exception rate
-   exception type distribution
-   false-match rate
-   false-exception rate
-   duplicate-detection accuracy
-   human override rate
-   average processing time
-   average human-review time
-   AI/API cost per invoice

## Why this architecture?

The prototype intentionally avoids asking a single AI model to decide
everything.

``` text
AI
  -> understands documents
  -> normalizes fields
  -> explains exceptions

Deterministic code
  -> compares financial values
  -> detects known exceptions
  -> applies routing policy

Human reviewer
  -> resolves exceptions
  -> approves or rejects
```

This separation makes the prototype easier to explain, test, audit, and
evolve toward a production-grade accounts-payable workflow.

## Disclaimer

This project is intended as a prototype/demo for invoice-processing
workflow automation. It should not be used to authorize or execute real
financial transactions without appropriate production controls, security
review, validation, and human/accounting oversight.
