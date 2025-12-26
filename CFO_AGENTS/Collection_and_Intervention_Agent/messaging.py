def draft_message(customer, item, intervention):
    base = f"""
Hi {customer['name']},

This is a reminder regarding Invoice {item['invoice_no']} 
overdue by {item['days_overdue']} days (₹{item['amount']:,}).
"""

    if intervention == "early_payment_discount":
        return base + "\nWe can offer a limited-time settlement discount."
    if intervention == "structured_payment_plan":
        return base + "\nLet’s discuss a short payment plan to close this."
    if intervention == "upfront_payment_or_block":
        return base + "\nImmediate payment required to avoid service disruption."
    if intervention == "legal_escalation":
        return base + "\nThis may be escalated if unresolved."
    
    return base + "\nPlease confirm payment timeline."
