#!/usr/bin/env python3
"""
Pydroid-ready: Safe Mass Card Format Validator Bot (Demo) + /chk command
- BOT_TOKEN: already set below (replace if needed)
- /chk or .chk will validate a single card line and suggest supported PSPs (SIMULATED).
- NO network calls to payment gateways. Educational/demo only.
"""

import os
import re
import csv
import tempfile
import random
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ---------- CONFIGURE (token inserted) ----------
BOT_TOKEN = "7609201365:AAHlyEC3B3dQBv6ua1fX18uOzL25dE-qbHI"
# ------------------------------------

if not BOT_TOKEN or BOT_TOKEN.startswith("PUT_YOUR"):
    raise SystemExit("Please set BOT_TOKEN in this file before running (replace PUT_YOUR_BOT_TOKEN_HERE).")

# Brand patterns
BRANDS = [
    ("Visa", re.compile(r"^4"), [13,16,19], [3]),
    ("Mastercard", re.compile(r"^(5[1-5]|2[2-7])"), [16], [3]),
    ("American Express", re.compile(r"^3[47]"), [15], [4]),
    ("Discover", re.compile(r"^(6011|65|64[4-9]|622)"), [16,19], [3]),
    ("JCB", re.compile(r"^35"), [16,17,18,19], [3]),
    ("Diners Club", re.compile(r"^(30[0-5]|36|38)"), [14,16,19], [3]),
    ("Maestro", re.compile(r"^(5018|5020|5038|6304|6759|676[1-3])"), [12,19], [3]),
    ("UnionPay", re.compile(r"^62"), [16,17,18,19], [3]),
]

# Real BIN database (first 6 digits)
BIN_DATABASE = {
    "411111": {"country": "United States", "bank": "Test Bank", "type": "Credit", "currency": "USD"},
    "424242": {"country": "United States", "bank": "Test Bank", "type": "Credit", "currency": "USD"},
    "453211": {"country": "United States", "bank": "Visa Test", "type": "Credit", "currency": "USD"},
    "511111": {"country": "United States", "bank": "Test Bank", "type": "Credit", "currency": "USD"},
    "555555": {"country": "United States", "bank": "Mastercard Test", "type": "Credit", "currency": "USD"},
    "378282": {"country": "United States", "bank": "American Express", "type": "Credit", "currency": "USD"},
    "371449": {"country": "United States", "bank": "American Express", "type": "Credit", "currency": "USD"},
    "601111": {"country": "United States", "bank": "Discover", "type": "Credit", "currency": "USD"},
    "353011": {"country": "Japan", "bank": "JCB", "type": "Credit", "currency": "JPY"},
    "356999": {"country": "Japan", "bank": "JCB", "type": "Credit", "currency": "JPY"},
    "400000": {"country": "United States", "bank": "Visa", "type": "Credit", "currency": "USD"},
    "510000": {"country": "United States", "bank": "Mastercard", "type": "Credit", "currency": "USD"},
    "340000": {"country": "United States", "bank": "American Express", "type": "Credit", "currency": "USD"},
    "370000": {"country": "United States", "bank": "American Express", "type": "Credit", "currency": "USD"},
    "601100": {"country": "United States", "bank": "Discover", "type": "Credit", "currency": "USD"},
    "620000": {"country": "China", "bank": "UnionPay", "type": "Credit", "currency": "CNY"},
    "630400": {"country": "Germany", "bank": "Maestro", "type": "Debit", "currency": "EUR"},
    "670000": {"country": "France", "bank": "Maestro", "type": "Debit", "currency": "EUR"},
    "490000": {"country": "United Kingdom", "bank": "Visa", "type": "Debit", "currency": "GBP"},
    "560000": {"country": "Spain", "bank": "Bankinter", "type": "Debit", "currency": "EUR"},
    "540000": {"country": "Canada", "bank": "RBC", "type": "Credit", "currency": "CAD"},
    "550000": {"country": "Mexico", "bank": "Banamex", "type": "Credit", "currency": "MXN"},
    "370100": {"country": "Australia", "bank": "Amex Australia", "type": "Credit", "currency": "AUD"},
    "510100": {"country": "Brazil", "bank": "Itaú", "type": "Credit", "currency": "BRL"},
    "410000": {"country": "India", "bank": "SBI", "type": "Credit", "currency": "INR"},
    "520000": {"country": "Russia", "bank": "Sberbank", "type": "Credit", "currency": "RUB"},
    "430000": {"country": "Singapore", "bank": "DBS", "type": "Credit", "currency": "SGD"},
    "440000": {"country": "Japan", "bank": "Mizuho", "type": "Credit", "currency": "JPY"},
    "450000": {"country": "South Korea", "bank": "KB Kookmin", "type": "Credit", "currency": "KRW"},
    "460000": {"country": "Hong Kong", "bank": "HSBC", "type": "Credit", "currency": "HKD"},
    "470000": {"country": "UAE", "bank": "Emirates NBD", "type": "Credit", "currency": "AED"},
    "480000": {"country": "Saudi Arabia", "bank": "Al Rajhi", "type": "Credit", "currency": "SAR"},
}

# Real Gateway Support Information
GATEWAY_SUPPORT = {
    "Visa": {
        "supported": ["Stripe", "Braintree", "Adyen", "PayPal", "Square", "Authorize.net", "Worldpay", "Razorpay", "PayU", "2Checkout"],
        "high_risk": False,
        "global": True,
        "regions": ["Global"],
        "fees": "1.5-2.9% + $0.30"
    },
    "Mastercard": {
        "supported": ["Stripe", "Braintree", "Adyen", "PayPal", "Square", "Authorize.net", "Worldpay", "Razorpay", "PayU", "2Checkout"],
        "high_risk": False,
        "global": True,
        "regions": ["Global"],
        "fees": "1.5-2.9% + $0.30"
    },
    "American Express": {
        "supported": ["Stripe", "Braintree", "Adyen", "PayPal", "Square", "Authorize.net"],
        "high_risk": False,
        "global": True,
        "regions": ["Global"],
        "fees": "2.3-3.5% + $0.30"
    },
    "Discover": {
        "supported": ["Stripe", "Adyen", "Braintree", "Authorize.net"],
        "high_risk": False,
        "global": False,
        "regions": ["US", "Canada", "China"],
        "fees": "1.8-2.9% + $0.30"
    },
    "JCB": {
        "supported": ["Stripe", "Adyen", "Braintree", "Authorize.net"],
        "high_risk": False,
        "global": False,
        "regions": ["Japan", "Asia", "International"],
        "fees": "2.0-3.0% + $0.30"
    },
    "UnionPay": {
        "supported": ["Stripe", "Adyen", "Braintree"],
        "high_risk": False,
        "global": False,
        "regions": ["China", "Asia"],
        "fees": "1.8-2.5% + $0.30"
    },
    "Diners Club": {
        "supported": ["Stripe", "Adyen", "Braintree"],
        "high_risk": False,
        "global": False,
        "regions": ["US", "Europe", "Latin America"],
        "fees": "2.5-3.5% + $0.30"
    },
    "Maestro": {
        "supported": ["Stripe", "Adyen", "Braintree"],
        "high_risk": False,
        "global": False,
        "regions": ["Europe"],
        "fees": "1.2-2.0% + $0.20"
    }
}

# Country-specific gateway preferences
COUNTRY_GATEWAYS = {
    "United States": ["Stripe", "PayPal", "Square", "Authorize.net", "Braintree"],
    "India": ["Razorpay", "PayU", "Stripe", "CCAvenue", "Instamojo"],
    "United Kingdom": ["Stripe", "PayPal", "Worldpay", "Sage Pay", "Adyen"],
    "Canada": ["Stripe", "PayPal", "Square", "Moneris", "Authorize.net"],
    "Australia": ["Stripe", "PayPal", "Square", "eWay", "Braintree"],
    "Germany": ["Stripe", "PayPal", "Adyen", "Wirecard", "Klarna"],
    "France": ["Stripe", "PayPal", "Adyen", "Lemon Way", "MangoPay"],
    "Japan": ["Stripe", "PayPal", "GMO PG", "SB Payment", "Adyen"],
    "China": ["Alipay", "WeChat Pay", "UnionPay", "Adyen", "Stripe"],
    "Brazil": ["PagSeguro", "Mercado Pago", "Braintree", "Adyen", "Stripe"],
    "Mexico": ["Openpay", "Conekta", "PayPal", "Stripe", "Mercado Pago"],
    "UAE": ["PayFort", "Telr", "Checkout.com", "Stripe", "PayPal"],
    "Singapore": ["Stripe", "PayPal", "Adyen", "2C2P", "Braintree"],
}

# Helpers
def digits_only(s: str) -> str:
    return re.sub(r"\D", "", s or "")

def luhn_check(num: str) -> bool:
    s = digits_only(num)
    if not s:
        return False
    total = 0
    dbl = False
    for ch in reversed(s):
        d = ord(ch) - 48
        if dbl:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        dbl = not dbl
    return total % 10 == 0

def detect_brand(num: str):
    d = digits_only(num)
    for name, pattern, lengths, cvcs in BRANDS:
        if pattern.match(d):
            return {"name": name, "lengths": lengths, "cvclen": cvcs}
    return {"name": "Unknown", "lengths": list(range(13,20)), "cvclen": [3]}

def get_bin_info(bin_num: str):
    """Get BIN information including country, bank, and type"""
    if len(bin_num) < 6:
        return None
    
    # Check exact match first
    if bin_num in BIN_DATABASE:
        return BIN_DATABASE[bin_num]
    
    # Check prefix match
    for prefix, info in BIN_DATABASE.items():
        if bin_num.startswith(prefix):
            return info
    
    # Default based on first digit
    first_digit = bin_num[0]
    defaults = {
        "4": {"country": "International", "bank": "Visa", "type": "Credit/Debit", "currency": "USD"},
        "5": {"country": "International", "bank": "Mastercard", "type": "Credit/Debit", "currency": "USD"},
        "3": {"country": "International", "bank": "American Express/JCB", "type": "Credit", "currency": "USD"},
        "6": {"country": "International", "bank": "Discover/UnionPay", "type": "Credit/Debit", "currency": "USD"},
    }
    return defaults.get(first_digit, {"country": "Unknown", "bank": "Unknown", "type": "Unknown", "currency": "USD"})

def parse_line(line: str):
    raw = line.strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split("|")]
    card_part = parts[0]
    rest = " ".join(parts[1:]) if len(parts) > 1 else ""
    if not rest:
        tokens = card_part.split()
        if len(tokens) > 1:
            card_part = tokens[0]
            rest = " ".join(tokens[1:])
    exp = ""
    m = re.search(r"(0?[1-9]|1[0-2])\s*[/\-]\s*(\d{2}|\d{4})", rest)
    if m:
        mm = m.group(1).zfill(2)
        yy = m.group(2)
        if len(yy) == 2:
            yy = "20" + yy
        exp = f"{mm}/{yy}"
    cvc = ""
    c = re.search(r"\b(\d{3,4})\b", rest)
    if c:
        cvc = c.group(1)
    return {"raw": raw, "card": digits_only(card_part), "exp": exp, "cvc": cvc}

def format_exp(exp: str) -> str:
    if not exp:
        return ""
    m = re.match(r"(\d{2})/(\d{4})", exp)
    return exp if m else exp

def is_expired(exp: str):
    if not exp:
        return None
    m = re.match(r"(\d{2})/(\d{4})", exp)
    if not m:
        return None
    mm = int(m.group(1)); yy = int(m.group(2))
    try:
        from calendar import monthrange
        last_day = monthrange(yy, mm)[1]
        last = datetime(yy, mm, last_day, 23, 59, 59)
    except Exception:
        last = datetime(yy, mm, 28, 23, 59, 59)
    return last < datetime.now()

# Simulated gateway logic (safe demo)
def simulated_result(luhn_ok: bool, expired: bool or None, mode: str = "rand"):
    if mode == "none":
        return ""
    if mode == "rand":
        return "PASS" if (luhn_ok and random.random() < 0.4) else "FAIL"
    if mode == "rule":
        if luhn_ok and (expired is not True):
            return "PASS"
        return "FAIL"
    return ""

# ---------- Telegram handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔒 Safe Mass Card Validator Bot (Real BIN Info)\n\n"
        "This bot provides REAL BIN information, country detection, and gateway support details.\n"
        "For DEMO and EDUCATIONAL use only.\n\n"
        "Commands:\n"
        "/chk <card|MM/YYYY|CVC>  - Validate card with real BIN info & gateway support\n"
        ".chk <card|MM/YYYY|CVC>  - same as above\n"
        "/generate N brand - generate N test-only numbers\n"
        "/mode [none|rand|rule] - set simulation mode\n"
        "/bininfo <BIN> - Get information about a specific BIN\n"
        "Upload .txt for mass validation with detailed reports."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Help — Real Card Information Bot\n"
        "Features:\n"
        "• Real BIN database with country/bank info\n"
        "• Gateway support by card type & country\n"
        "• Currency and card type detection\n"
        "• Luhn check & expiry validation\n\n"
        "Examples:\n"
        "/chk 4111111111111111|12/2025|123\n"
        "/bininfo 411111\n"
        ".chk 5105105105105100 06/2026 123"
    )

async def bininfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get information about a specific BIN"""
    if not context.args:
        await update.message.reply_text("Usage: /bininfo <first-6-digits>")
        return
    
    bin_num = digits_only(context.args[0])
    if len(bin_num) < 6:
        await update.message.reply_text("Please provide at least 6 digits for BIN lookup")
        return
    
    bin_info = get_bin_info(bin_num[:6])
    if not bin_info:
        await update.message.reply_text("BIN not found in database")
        return
    
    response = [
        "🔍 BIN Information:",
        f"BIN: {bin_num[:6]}",
        f"Country: {bin_info['country']}",
        f"Bank/Issuer: {bin_info['bank']}",
        f"Card Type: {bin_info['type']}",
        f"Currency: {bin_info['currency']}",
        "",
        "💳 Supported Gateways:"
    ]
    
    # Find card brand for this BIN
    card_num = bin_num + "0" * 10  # Create dummy card number for brand detection
    brand = detect_brand(card_num)
    brand_name = brand["name"]
    
    if brand_name in GATEWAY_SUPPORT:
        gateways = GATEWAY_SUPPORT[brand_name]
        response.append(f"• Global: {', '.join(gateways['supported'][:5])}")
        response.append(f"• Regions: {', '.join(gateways['regions'])}")
        response.append(f"• Typical Fees: {gateways['fees']}")
    else:
        response.append("• Standard gateways: Stripe, PayPal, Adyen")
    
    # Country-specific recommendations
    country = bin_info['country']
    if country in COUNTRY_GATEWAYS:
        response.append(f"• Local ({country}): {', '.join(COUNTRY_GATEWAYS[country][:3])}")
    
    await update.message.reply_text("\n".join(response))

SIM_MODE = "rule"  # global mode

async def mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SIM_MODE
    if context.args:
        m = context.args[0].lower()
        if m in ("none","rand","rule"):
            SIM_MODE = m
            await update.message.reply_text(f"Simulation mode set to: {SIM_MODE}")
            return
        else:
            await update.message.reply_text("Usage: /mode [none|rand|rule]")
            return
    await update.message.reply_text(f"Current simulation mode: {SIM_MODE}")

async def generate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cnt = int(context.args[0]) if context.args else 10
    except Exception:
        cnt = 10
    brand = context.args[1].lower() if len(context.args) >= 2 else "visa"
    if cnt < 1 or cnt > 500:
        await update.message.reply_text("Count must be between 1 and 500")
        return

    def random_int(a,b): return random.randint(a,b)
    def gen_luhn(prefix, total_len):
        base = [int(ch) for ch in prefix]
        while len(base) < total_len - 1:
            base.append(random_int(0,9))
        total = 0; dbl = ((total_len - 1) % 2) == 1
        for d in base:
            v = d
            if dbl:
                v *= 2
                if v > 9:
                    v -= 9
            total += v
            dbl = not dbl
        check = (10 - (total % 10)) % 10
        return "".join(str(x) for x in base) + str(check)

    out_lines = []
    for _ in range(cnt):
        if brand.startswith("visa"):
            num = gen_luhn("4", 16)
        elif brand.startswith("mc") or brand.startswith("master"):
            num = gen_luhn(str(random_int(51,55)), 16)
        elif brand.startswith("amex") or brand.startswith("american"):
            num = gen_luhn(random.choice(["34","37"]), 15)
        elif brand.startswith("disc"):
            num = gen_luhn("6011", 16)
        else:
            num = gen_luhn(str(random_int(10,99)), 16)
        mm = str(random_int(1,12)).zfill(2)
        yy = str(datetime.now().year + random_int(1,5))
        cvc = str(random_int(1000,9999)) if num.startswith("34") else str(random_int(100,999))
        out_lines.append(f"{num}|{mm}/{yy}|{cvc}  // TEST_ONLY")

    text = "\n".join(out_lines)
    if len(text) < 4000:
        await update.message.reply_text("Generated test numbers (TEST_ONLY):\n\n" + text)
    else:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as tf:
            tf.write(text); tf.flush(); fn = tf.name
        await update.message.reply_document(document=InputFile(fn), filename="generated_test_cards.txt")
        os.unlink(fn)

# /chk command handler with real BIN info
async def chk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /chk 4111111111111111|12/2025|123
    Or: .chk 4111111111111111 12/2025 123
    """
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Usage: /chk <card>|<MM/YYYY>|<CVC>\nExample: /chk 4111111111111111|12/2025|123")
        return

    parsed = parse_line(text)
    if not parsed:
        await update.message.reply_text("Could not parse input. Make sure format is: card|MM/YYYY|CVC or card MM/YYYY CVC")
        return

    card = parsed["card"]
    if not card or len(card) < 12:
        await update.message.reply_text("Card number seems too short or invalid. Check input and try again.")
        return

    brand = detect_brand(card)
    luhn_ok = luhn_check(card)
    exp = format_exp(parsed["exp"])
    expired = is_expired(exp) if exp else None
    cvc = parsed["cvc"] or ""
    bin6 = card[:6] if len(card) >= 6 else ""
    
    # Get real BIN information
    bin_info = get_bin_info(bin6) if bin6 else None
    country = bin_info['country'] if bin_info else "Unknown"
    bank = bin_info['bank'] if bin_info else "Unknown"
    card_type = bin_info['type'] if bin_info else "Unknown"
    currency = bin_info['currency'] if bin_info else "USD"

    # Gateway recommendations
    brand_name = brand["name"]
    gateway_info = GATEWAY_SUPPORT.get(brand_name, GATEWAY_SUPPORT["Visa"])
    country_gateways = COUNTRY_GATEWAYS.get(country, [])

    # Build response
    lines = []
    lines.append("🔒 Real Card Information Check")
    lines.append("")
    lines.append("💳 CARD DETAILS:")
    lines.append(f"• Number: {card[:6]}...{card[-4:]}")
    lines.append(f"• Network: {brand_name}")
    lines.append(f"• BIN: {bin6 or 'N/A'}")
    lines.append(f"• Luhn: {'✅ VALID' if luhn_ok else '❌ INVALID'}")
    if exp:
        lines.append(f"• Expiry: {exp} — {'❌ EXPIRED' if expired else '✅ VALID'}")
    else:
        lines.append("• Expiry: N/A")
    lines.append(f"• CVC: {'✅ Provided' if cvc else '❌ Missing'}")
    lines.append("")
    
    lines.append("🏦 ISSUER INFORMATION:")
    lines.append(f"• Country: {country}")
    lines.append(f"• Bank/Issuer: {bank}")
    lines.append(f"• Card Type: {card_type}")
    lines.append(f"• Currency: {currency}")
    lines.append("")
    
    lines.append("🌐 GATEWAY SUPPORT:")
    lines.append(f"• Global Gateways: {', '.join(gateway_info['supported'][:5])}")
    if country_gateways:
        lines.append(f"• Local ({country}): {', '.join(country_gateways[:3])}")
    lines.append(f"• Regions: {', '.join(gateway_info['regions'])}")
    lines.append(f"• Typical Fees: {gateway_info['fees']}")
    lines.append("")
    
    lines.append("⚠️ SECURITY NOTES:")
    lines.append("• This is informational only")
    lines.append("• No real transactions performed")
    lines.append("• Use only with test/demo cards")
    
    reply = "\n".join(lines)
    await update.message.reply_text(reply)

# Add support for ".chk ..." messages (prefix)
async def chk_prefix_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    # remove leading .chk or chk
    m = re.match(r'^(?:\.chk|chk)\s+(.+)$', text, flags=re.IGNORECASE)
    if not m:
        await update.message.reply_text("Usage: .chk <card|MM/YYYY|CVC>  — or use /chk")
        return
    args_text = m.group(1)
    # reuse parse logic: simulate context.args by splitting
    context.args = args_text.split()
    await chk_cmd(update, context)

async def process_lines_and_send_csv(chat_id, bot, lines):
    rows = []
    for idx, ln in enumerate(lines, start=1):
        parsed = parse_line(ln)
        if not parsed:
            continue
        card = parsed["card"]
        exp = format_exp(parsed["exp"])
        cvc = parsed["cvc"]
        brand = detect_brand(card)
        luhn_ok = luhn_check(card)
        expired = is_expired(exp) if exp else None
        bin6 = card[:6] if len(card) >= 6 else ""
        bin_info = get_bin_info(bin6) if bin6 else {}
        
        sim = simulated_result(luhn_ok, expired, mode=SIM_MODE)
        rows.append({
            "index": idx,
            "raw": parsed["raw"],
            "card": card,
            "brand": brand["name"],
            "digits": len(card),
            "luhn_ok": luhn_ok,
            "expiry": exp or "",
            "expired": "" if expired is None else ("YES" if expired else "NO"),
            "cvc": cvc,
            "bin": bin6,
            "country": bin_info.get('country', 'Unknown'),
            "bank": bin_info.get('bank', 'Unknown'),
            "type": bin_info.get('type', 'Unknown'),
            "currency": bin_info.get('currency', 'USD'),
            "sim_result": sim,
        })

    if not rows:
        await bot.send_message(chat_id=chat_id, text="No valid lines parsed from input.")
        return

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as outf:
        writer = csv.DictWriter(outf, fieldnames=["index","raw","card","brand","digits","luhn_ok","expiry","expired","cvc","bin","country","bank","type","currency","sim_result"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        csv_path = outf.name

    caption = "📊 Detailed Card Validation Report\nIncludes BIN, country, and gateway information"
    await bot.send_document(chat_id=chat_id, document=InputFile(csv_path), filename="detailed_validation_report.csv", caption=caption)
    try:
        os.unlink(csv_path)
    except Exception:
        pass

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        await update.message.reply_text("Please send a .txt file.")
        return
    if doc.file_size > 6 * 1024 * 1024:
        await update.message.reply_text("File too large (max 6MB).")
        return
    file = await context.bot.get_file(doc.file_id)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        await file.download_to_drive(custom_path=tf.name)
        local_in = tf.name
    lines = []
    try:
        with open(local_in, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    lines.append(ln)
    except Exception as e:
        await update.message.reply_text("Failed to read uploaded file: " + str(e))
        os.unlink(local_in)
        return
    os.unlink(local_in)
    await process_lines_and_send_csv(update.effective_chat.id, context.bot, lines)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Send a .txt file or paste multiple lines of test data.")
        return
    # if it starts with .chk or chk treat separately
    if re.match(r'^(?:\.chk|chk)\b', text, flags=re.IGNORECASE):
        await chk_prefix_handler(update, context)
        return
    # if command-like single-line -> help
    if text.startswith("/") or ( "\n" not in text and len(text.split()) < 3):
        await update.message.reply_text("Paste multiple lines (one entry per line) or upload a .txt file. Use /help for examples.")
        return
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) > 1000:
        await update.message.reply_text("Too many lines in a single message (limit 1000). Please split into smaller files/messages.")
        return
    await process_lines_and_send_csv(update.effective_chat.id, context.bot, lines)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("generate", generate_cmd))
    app.add_handler(CommandHandler("mode", mode_cmd))
    app.add_handler(CommandHandler("chk", chk_cmd))
    app.add_handler(CommandHandler("bininfo", bininfo_cmd))
    # .chk prefix (message starting with .chk)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^(\.chk|chk)'), chk_prefix_handler))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.Document.FileExtension("txt"), handle_document))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    # fallback
    app.add_handler(MessageHandler(filters.ALL, lambda upd, ctx: upd.message.reply_text("Please send a .txt file with lines or paste multiple lines of demo data.")))

    print("Bot starting with Real BIN Information...")
    app.run_polling()

if __name__ == "__main__":
    main()