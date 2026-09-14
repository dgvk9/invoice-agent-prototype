ROUTING_RULES = {
    "PRICE_VARIANCE": "Procurement",
    "QUANTITY_VARIANCE": "Receiving",
    "MISSING_PO": "Accounts Payable",
    "VENDOR_MISMATCH": "Accounts Payable",
    "CURRENCY_MISMATCH": "Accounts Payable",
    "TOTAL_MISMATCH": "Accounts Payable",
    "LINE_ITEM_COUNT_MISMATCH": "Accounts Payable",
    "DUPLICATE_INVOICE": "Accounts Payable",
    "LOW_CONFIDENCE": "Accounts Payable",
    "PO_NUMBER_MISMATCH": "Accounts Payable",
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
