ROUTING_RULES = {

    # ---------------------------------------------------------
    # Duplicate detection
    # ---------------------------------------------------------
    "DUPLICATE_INVOICE": "Accounts Payable",

    # ---------------------------------------------------------
    # Extraction / confidence validation
    # ---------------------------------------------------------
    "LOW_CONFIDENCE": "Accounts Payable",
    "EXTRACTION_VALIDATION_ERROR": "Accounts Payable",
    

    # ---------------------------------------------------------
    # Financial validation
    # Checks whether the invoice or PO is internally
    # mathematically consistent before matching begins.
    # ---------------------------------------------------------
    "INVOICE_CALCULATION_ERROR": "Accounts Payable",
    "PO_CALCULATION_ERROR": "Accounts Payable",
    "LINE_CALCULATION_ERROR": "Accounts Payable",
    "LINE_SUM_MISMATCH": "Accounts Payable",

    # ---------------------------------------------------------
    # Invoice ↔ Purchase Order matching
    # Checks whether the two documents agree with each other.
    # ---------------------------------------------------------
    "PRICE_VARIANCE": "Procurement",
    "QUANTITY_VARIANCE": "Receiving",

    "VENDOR_MISMATCH": "Accounts Payable",
    "CURRENCY_MISMATCH": "Accounts Payable",
    "PO_NUMBER_MISMATCH": "Accounts Payable",
    "TOTAL_MISMATCH": "Accounts Payable",
    "TAX_VARIANCE": "Accounts Payable",

    "LINE_AMOUNT_VARIANCE": "Accounts Payable",
    "LINE_ITEM_COUNT_MISMATCH": "Accounts Payable",
    "UNMATCHED_INVOICE_LINE": "Accounts Payable",
    "UNMATCHED_PO_LINE": "Accounts Payable",

    # ---------------------------------------------------------
    # Purchase Order availability
    # ---------------------------------------------------------
    "MISSING_PO": "Accounts Payable",
}


def determine_route(exceptions):
    if not exceptions:
        return None

    routes = []

    for exception in exceptions:
        exception_type = exception["type"]
        route = ROUTING_RULES.get(
            exception_type,
            "Accounts Payable"
        )

        routes.append(route)

    # return unique routes
    return list(set(routes))
