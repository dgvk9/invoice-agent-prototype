def amounts_differ(actual, expected, tolerance=0.01):
    return abs(actual - expected) > tolerance


def validate_document_financials(
    document,
    document_type,
    tolerance=0.01
):
    """
    Validate arithmetic inside an extracted invoice or PO.

    This does NOT compare an invoice with a PO.
    It only asks whether the document is internally consistent.
    """

    exceptions = []

    label = (
        "Invoice"
        if document_type == "invoice"
        else "Purchase order"
    )

    # -----------------------------------------
    # 1. quantity × unit price = line amount
    # -----------------------------------------

    line_items = document.get("line_items") or []

    for index, item in enumerate(line_items, start=1):

        quantity = item.get("quantity")
        unit_price = item.get("unit_price")
        amount = item.get("amount")

        if (
            quantity is None
            or unit_price is None
            or amount is None
        ):
            continue

        expected_amount = quantity * unit_price

        if amounts_differ(
            amount,
            expected_amount,
            tolerance
        ):
            exceptions.append({
                "type": "LINE_CALCULATION_ERROR",
                "message": (
                    f"{label} line {index}: "
                    f"quantity {quantity} × unit price "
                    f"{unit_price} = {expected_amount:.2f}, "
                    f"but line amount is {amount:.2f}."
                ),
                "document": document_type,
                "line": index
            })

    # -----------------------------------------
    # 2. Sum of line amounts = subtotal
    # -----------------------------------------

    subtotal = document.get("subtotal")

    if subtotal is not None and line_items:

        line_amounts = [
            item.get("amount")
            for item in line_items
        ]

        if all(
            amount is not None
            for amount in line_amounts
        ):
            calculated_subtotal = sum(line_amounts)

            if amounts_differ(
                subtotal,
                calculated_subtotal,
                tolerance
            ):
                exceptions.append({
                    "type": "LINE_SUM_MISMATCH",
                    "message": (
                        f"{label} line items total "
                        f"{calculated_subtotal:.2f}, "
                        f"but subtotal is {subtotal:.2f}."
                    ),
                    "document": document_type
                })

    # -----------------------------------------
    # 3. subtotal + tax = total
    # -----------------------------------------

    tax = document.get("tax")
    total = document.get("total")

    if (
        subtotal is not None
        and tax is not None
        and total is not None
    ):
        expected_total = subtotal + tax

        if amounts_differ(
            total,
            expected_total,
            tolerance
        ):
            exceptions.append({
                "type": "INVOICE_CALCULATION_ERROR"
                if document_type == "invoice"
                else "PO_CALCULATION_ERROR",
                "message": (
                    f"{label} subtotal {subtotal:.2f} "
                    f"+ tax {tax:.2f} "
                    f"= {expected_total:.2f}, "
                    f"but total is {total:.2f}."
                ),
                "document": document_type
            })

    return exceptions