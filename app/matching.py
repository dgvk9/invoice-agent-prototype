from difflib import SequenceMatcher


def normalize_description(description):
    """
    Normalize a line-item description before comparing it.
    """
    if not description:
        return ""

    return " ".join(
        str(description)
        .lower()
        .strip()
        .split()
    )


def description_similarity(description_a, description_b):
    """
    Return a similarity score between 0 and 1.
    """
    a = normalize_description(description_a)
    b = normalize_description(description_b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


def match_line_items(
    invoice_items,
    po_items,
    tolerance=0.01,
    description_threshold=0.60
):
    """
    Match invoice lines to PO lines by description rather
    than assuming they appear in the same order.
    """

    exceptions = []
    line_matches = []

    unmatched_po_indexes = set(
        range(len(po_items))
    )

    for invoice_index, invoice_item in enumerate(
        invoice_items
    ):

        best_po_index = None
        best_score = 0.0

        # Find the best unused PO line based on description.
        for po_index in unmatched_po_indexes:

            po_item = po_items[po_index]

            score = description_similarity(
                invoice_item.get("description"),
                po_item.get("description")
            )

            if score > best_score:
                best_score = score
                best_po_index = po_index

        # No sufficiently similar PO line found.
        if (
            best_po_index is None
            or best_score < description_threshold
        ):
            exceptions.append({
                "type": "UNMATCHED_INVOICE_LINE",
                "message": (
                    f"No matching PO line found for "
                    f"invoice line "
                    f"'{invoice_item.get('description')}'."
                )
            })

            line_matches.append({
                "invoice_line": invoice_index + 1,
                "po_line": None,
                "description": invoice_item.get(
                    "description"
                ),
                "status": "UNMATCHED",
                "description_similarity": round(
                    best_score,
                    3
                )
            })

            continue

        po_item = po_items[best_po_index]

        unmatched_po_indexes.remove(
            best_po_index
        )

        line_exceptions = []

        invoice_quantity = (
            invoice_item.get("quantity") or 0
        )

        po_quantity = (
            po_item.get("quantity") or 0
        )

        invoice_unit_price = (
            invoice_item.get("unit_price") or 0
        )

        po_unit_price = (
            po_item.get("unit_price") or 0
        )

        invoice_amount = (
            invoice_item.get("amount") or 0
        )

        po_amount = (
            po_item.get("amount") or 0
        )

        # Quantity check
        if invoice_quantity > po_quantity + tolerance:

            exception = {
                "type": "QUANTITY_VARIANCE",
                "message": (
                    f"Quantity exceeds PO for "
                    f"'{invoice_item.get('description')}': "
                    f"invoice={invoice_quantity}, "
                    f"PO={po_quantity}"
                )
            }

            exceptions.append(exception)
            line_exceptions.append(
                "QUANTITY_VARIANCE"
            )

        # Unit price check
        price_difference = abs(
            invoice_unit_price -
            po_unit_price
        )

        if price_difference > tolerance:

            exception = {
                "type": "PRICE_VARIANCE",
                "message": (
                    f"Unit price mismatch for "
                    f"'{invoice_item.get('description')}': "
                    f"invoice={invoice_unit_price}, "
                    f"PO={po_unit_price}, "
                    f"difference={price_difference}"
                )
            }

            exceptions.append(exception)
            line_exceptions.append(
                "PRICE_VARIANCE"
            )

        # Line amount check
        amount_difference = abs(
            invoice_amount -
            po_amount
        )

        if amount_difference > tolerance:

            exception = {
                "type": "LINE_AMOUNT_VARIANCE",
                "message": (
                    f"Line amount mismatch for "
                    f"'{invoice_item.get('description')}': "
                    f"invoice={invoice_amount}, "
                    f"PO={po_amount}, "
                    f"difference={amount_difference}"
                )
            }

            exceptions.append(exception)
            line_exceptions.append(
                "LINE_AMOUNT_VARIANCE"
            )

        line_matches.append({
            "invoice_line": invoice_index + 1,
            "po_line": best_po_index + 1,
            "description": invoice_item.get(
                "description"
            ),
            "po_description": po_item.get(
                "description"
            ),
            "description_similarity": round(
                best_score,
                3
            ),
            "invoice_quantity": invoice_quantity,
            "po_quantity": po_quantity,
            "invoice_unit_price": (
                invoice_unit_price
            ),
            "po_unit_price": po_unit_price,
            "invoice_amount": invoice_amount,
            "po_amount": po_amount,
            "status": (
                "MATCH"
                if not line_exceptions
                else "EXCEPTION"
            ),
            "exceptions": line_exceptions
        })

    # PO lines that were never matched.
    for po_index in sorted(
        unmatched_po_indexes
    ):

        po_item = po_items[po_index]

        exceptions.append({
            "type": "UNMATCHED_PO_LINE",
            "message": (
                f"PO line "
                f"'{po_item.get('description')}' "
                f"has no matching invoice line."
            )
        })

        line_matches.append({
            "invoice_line": None,
            "po_line": po_index + 1,
            "description": None,
            "po_description": po_item.get(
                "description"
            ),
            "status": "UNMATCHED"
        })

    return line_matches, exceptions


def match_invoice_to_po(
    invoice,
    po,
    tolerance=0.01
):

    exceptions = []

    # 1. Check whether PO exists
    if po is None:
        return {
            "decision": "EXCEPTION",
            "reason": "PURCHASE_ORDER_NOT_FOUND",
            "exceptions": [
                {
                    "type": "MISSING_PO",
                    "message": (
                        "No matching purchase order "
                        "was found."
                    )
                }
            ],
            "line_item_matching": []
        }

    # 2. PO number check
    if (
        invoice.get("po_number")
        != po.get("po_number")
    ):
        exceptions.append({
            "type": "PO_NUMBER_MISMATCH",
            "message": (
                f"Invoice references "
                f"{invoice.get('po_number')} "
                f"but uploaded PO is "
                f"{po.get('po_number')}."
            )
        })

    # 3. Vendor check
    invoice_vendor = (
        invoice.get("vendor") or ""
    ).lower()

    po_vendor = (
        po.get("vendor") or ""
    ).lower()

    if invoice_vendor != po_vendor:
        exceptions.append({
            "type": "VENDOR_MISMATCH",
            "message": (
                f"Vendor mismatch: "
                f"invoice={invoice.get('vendor')} "
                f"PO={po.get('vendor')}"
            )
        })

    # 4. Currency check
    if (
        invoice.get("currency")
        != po.get("currency")
    ):
        exceptions.append({
            "type": "CURRENCY_MISMATCH",
            "message": (
                f"Currency mismatch: "
                f"invoice={invoice.get('currency')} "
                f"PO={po.get('currency')}"
            )
        })

    # 5. Validate invoice arithmetic
    invoice_subtotal = invoice.get(
        "subtotal"
    )

    invoice_tax = invoice.get("tax")

    invoice_total = invoice.get("total")

    if (
        invoice_subtotal is not None
        and invoice_tax is not None
        and invoice_total is not None
    ):

        calculated_total = (
            invoice_subtotal +
            invoice_tax
        )

        calculation_difference = abs(
            calculated_total -
            invoice_total
        )

        if calculation_difference > tolerance:
            exceptions.append({
                "type": "INVOICE_CALCULATION_ERROR",
                "message": (
                    f"Invoice subtotal + tax does "
                    f"not equal total: "
                    f"subtotal={invoice_subtotal}, "
                    f"tax={invoice_tax}, "
                    f"total={invoice_total}, "
                    f"expected={calculated_total}"
                )
            })

    # 6. Tax comparison
    po_tax = po.get("tax")

    if (
        invoice_tax is not None
        and po_tax is not None
    ):

        tax_difference = abs(
            invoice_tax -
            po_tax
        )

        if tax_difference > tolerance:
            exceptions.append({
                "type": "TAX_VARIANCE",
                "message": (
                    f"Tax mismatch: "
                    f"invoice={invoice_tax}, "
                    f"PO={po_tax}, "
                    f"difference={tax_difference}"
                )
            })

    # 7. Total comparison
    po_total = po.get("total")

    if (
        invoice_total is not None
        and po_total is not None
    ):

        total_difference = abs(
            invoice_total -
            po_total
        )

        if total_difference > tolerance:
            exceptions.append({
                "type": "TOTAL_MISMATCH",
                "message": (
                    f"Total mismatch: "
                    f"invoice={invoice_total}, "
                    f"PO={po_total}, "
                    f"difference={total_difference}"
                )
            })

    # 8. Match line items
    invoice_items = (
        invoice.get("line_items") or []
    )

    po_items = (
        po.get("line_items") or []
    )

    line_matches, line_exceptions = (
        match_line_items(
            invoice_items,
            po_items,
            tolerance
        )
    )

    exceptions.extend(
        line_exceptions
    )

    # 9. Final decision
    if exceptions:
        return {
            "decision": "EXCEPTION",
            "reason": "MATCHING_FAILURE",
            "exceptions": exceptions,
            "line_item_matching": line_matches
        }

    return {
        "decision": "MATCH",
        "reason": "INVOICE_MATCHES_PO",
        "exceptions": [],
        "line_item_matching": line_matches
    }