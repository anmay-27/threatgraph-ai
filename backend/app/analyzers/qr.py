from urllib.parse import urlsplit, parse_qs


def classify_qr(value):
    lower = value.lower()
    if lower.startswith(("http://", "https://")):
        return {"type": "URL", "destination": value}
    if lower.startswith("upi://pay"):
        q = parse_qs(urlsplit(value).query)
        return {
            "type": "UPI",
            "scheme": "upi",
            "payment_identifier": q.get("pa", [""])[0][:200],
            "payee": q.get("pn", [""])[0][:200],
            "amount": q.get("am", [""])[0][:40],
            "note": q.get("tn", [""])[0][:500],
            "limitation": "Decoded instructions only; payee identity and legitimacy are not verified. No payment initiated.",
        }
    if lower.startswith("wifi:"):
        return {
            "type": "WIFI",
            "limitation": "WiFi QR detected; credentials are not included in the report.",
        }
    if lower.startswith(("begin:vcard", "mecard:")):
        return {"type": "CONTACT"}
    if lower.startswith(("bitcoin:", "ethereum:", "payto:")):
        return {"type": "PAYMENT_URI", "scheme": urlsplit(value).scheme}
    return {"type": "TEXT"}
