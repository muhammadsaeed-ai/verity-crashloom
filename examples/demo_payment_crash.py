def split_invoice_total(invoice: dict, recipients: list, stripe_api_key: str):
    return invoice["subtotal"] / len(recipients)

if __name__ == "__main__":
    split_invoice_total({"subtotal": 1000}, [], "example-not-a-real-key")
