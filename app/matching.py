def match_invoice_to_po(invoice, po, tolerance=0.01):

    exceptions = []

    # 1. Check whether PO exists first
    if po is None:
        return {
            "decision": "EXCEPTION",
            "reason": "PURCHASE_ORDER_NOT_FOUND",
            "exceptions": [
                {
                    "type": "MISSING_PO",
                    "message": "No matching purchase order was found."
                }
            ]
        }

    # 2. PO number check
    if invoice.get("po_number") != po.get("po_number"):
        exceptions.append({
            "type": "PO_NUMBER_MISMATCH",
            "message": (
                f"Invoice references {invoice.get('po_number')} "
                f"but uploaded PO is {po.get('po_number')}."
            )
        })

    # 3. Vendor check
    if invoice["vendor"].lower() != po["vendor"].lower():
        exceptions.append({
            "type": "VENDOR_MISMATCH",
            "message": (
                f"Vendor mismatch: invoice={invoice['vendor']} "
                f"PO={po['vendor']}"
            )
        })

    # 4. Currency check
    if invoice["currency"] != po["currency"]:
        exceptions.append({
            "type": "CURRENCY_MISMATCH",
            "message": (
                f"Currency mismatch: invoice={invoice['currency']} "
                f"PO={po['currency']}"
            )
        })

    # 5. Total check
    invoice_total = invoice["total"]
    po_total = po["total"]

    difference = abs(invoice_total - po_total)

    if difference > tolerance:
        exceptions.append({
            "type": "TOTAL_MISMATCH",
            "message": (
                f"Total mismatch: invoice={invoice_total}, "
                f"PO={po_total}, difference={difference}"
            )
        })

    # 6. Line item checks
    invoice_items = invoice["line_items"]
    po_items = po["line_items"]

    if len(invoice_items) != len(po_items):
        exceptions.append({
            "type": "LINE_ITEM_COUNT_MISMATCH",
            "message": "Number of invoice line items does not match PO."
        })

    for invoice_item, po_item in zip(invoice_items, po_items):

        if invoice_item["quantity"] > po_item["quantity"]:
            exceptions.append({
                "type": "QUANTITY_VARIANCE",
                "message": (
                    f"Quantity exceeds PO: "
                    f"invoice={invoice_item['quantity']}, "
                    f"PO={po_item['quantity']}"
                )
            })

        price_difference = abs(
            invoice_item["unit_price"] -
            po_item["unit_price"]
        )

        if price_difference > tolerance:
            exceptions.append({
                "type": "PRICE_VARIANCE",
                "message": (
                    f"Unit price mismatch: "
                    f"invoice={invoice_item['unit_price']}, "
                    f"PO={po_item['unit_price']}"
                )
            })

    # 7. Return exception if anything failed
    if exceptions:
        return {
            "decision": "EXCEPTION",
            "reason": "MATCHING_FAILURE",
            "exceptions": exceptions
        }

    # 8. Otherwise it's a match
    return {
        "decision": "MATCH",
        "reason": "INVOICE_MATCHES_PO",
        "exceptions": []
    }