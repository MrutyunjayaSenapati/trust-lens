import re
from typing import Optional

from . import gemini
from .models import Entities, Evidence

EXTRACT_PROMPT = """You are an information extractor for a scam-investigation tool used in India.
Read the message (and image, if any) and return ONE JSON object with exactly these keys:
kind: one of "job_offer","seller","deal","property","other"
company: company/brand/seller name or null
role: job title or null
city: city mentioned or null
claimed_address: office/shop address claimed or null
phone: phone number or null
contact_email: email address of the sender/recruiter or null
website: website mentioned or null
product: product name for deals or null
claimed_price: number (INR) the item is offered at, or null
claimed_original_price: number (INR) the claimed original/MRP price, or null
payment_requested: true if the sender asks the user to pay any money (fee, deposit, kit, registration)
summary: one neutral sentence describing what the message offers
transcript: if an image was given, ALL text visible in it, verbatim; otherwise empty string
Do not invent facts. Use null when absent. The message may be in English, Hindi or Hinglish.

MESSAGE:
"""

FEE_RE = re.compile(r"(registration|security|training|processing|refundable|kit|verification|joining|onboarding)\s*(fee|fees|deposit|charges?|amount)|pay\s*(rs\.?|₹|inr)\s*[\d,]+|send\s+(money|₹|rs)|\bupi\b|paytm|phonepe|google\s*pay", re.I)
CHAT_ONLY_RE = re.compile(r"(whats\s?app|telegram)\s*(only|us|number|me|:|\+)|contact.*(whatsapp|telegram)|\bdm\b", re.I)
URGENCY_RE = re.compile(r"(limited\s+(seats|slots|vacanc)|hurry|last\s+date\s+today|within\s+\d+\s*(hours|hrs|mins)|immediate(ly)?\s+(joining|reply)|offer\s+expires|only\s+\d+\s+(seats|slots|left))", re.I)
NO_INTERVIEW_RE = re.compile(r"(without|no)\s+(any\s+)?(interview|exam|test|experience)|direct\s+(selection|joining)|selected\s+(directly|already)|100\s*%\s*(guarantee|placement|selection)", re.I)
UNREAL_PAY_RE = re.compile(r"(earn|salary|income)[^.\n]{0,25}(₹|rs\.?|inr)\s*[\d,]{5,}\s*(/|per|a)\s*(day|week)|(₹|rs\.?)\s*\d{2,3},?\d{3}\s*(per|/)\s*week", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}")
PRICE_RE = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]{3,})", re.I)
DEAL_RE = re.compile(r"\b(sale|discount|mrp|off|offer|deal|limited stock|stock|delivery|cod|cash on delivery|only)\b", re.I)
# the words right before "only ₹9,999" / "at ₹9,999" / "@ ₹9,999" are usually the product name
PRODUCT_RE = re.compile(r"((?:[A-Za-z0-9][\w+\-]*\s+){1,5}[A-Za-z0-9][\w+\-]*)\s*(?:only|at|for|just|now|@|:|-)?\s*(?:₹|rs\.?|inr)\s*[\d,]{3,}")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s)]+", re.I)


def heuristic_entities(text: str) -> Entities:
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)
    url = URL_RE.search(text)
    is_job = bool(re.search(r"intern|job|hiring|vacanc|offer letter|recruit|position|joining|salary|stipend", text, re.I))
    prices = [float(p.replace(",", "")) for p in PRICE_RE.findall(text)]
    is_deal = not is_job and bool(prices) and bool(DEAL_RE.search(text))
    kind = "job_offer" if is_job else ("deal" if is_deal else "other")
    product, claimed, original = None, None, None
    if is_deal:
        mrp = re.search(r"(?:mrp|original|was|worth|regular)[^\d₹]{0,12}(?:₹|rs\.?|inr)?\s*([\d,]{3,})", text, re.I)
        if mrp:
            original = float(mrp.group(1).replace(",", ""))
        sale = [p for p in prices if p != original]
        claimed = min(sale) if sale else None
        pm = PRODUCT_RE.search(text)
        product = re.sub(r"^(?:buy|get|order|grab|new|brand|now|only|at|for)\b\s*", "", pm.group(1).strip(), flags=re.I) if pm else None
    company = None
    m = re.search(r"(?:at|with|from|by|company[:\s])\s+([A-Z][\w&.-]*(?:\s+[A-Z][\w&.-]*){0,3}(?:\s+(?:Pvt|Ltd|LLP|Inc|Limited|Solutions|Technologies|Services|Global)\.?)*)", text)
    if m:
        company = m.group(1).strip()
    return Entities(
        kind=kind, company=company, contact_email=email.group(0) if email else None,
        phone=phone.group(0) if phone else None, website=url.group(0) if url else None,
        product=product, claimed_price=claimed, claimed_original_price=original,
        payment_requested=bool(FEE_RE.search(text)), summary=text.strip()[:160],
    )


def apply_resolved(ent: Entities, res) -> Entities:
    """Fill gaps from a link resolved through SerpApi; never overwrite what the message itself says."""
    if res is None or not res.found:
        return ent
    if res.kind != "other" and ent.kind in ("other",):
        ent.kind = res.kind
    for f in ("company", "role", "city"):
        if not getattr(ent, f) and getattr(res, f):
            setattr(ent, f, getattr(res, f))
    if ent.kind == "deal" and not ent.product:
        ent.product = re.sub(r"\s*[|:\-]\s*(Amazon|Flipkart|Myntra|Meesho|Buy).*$", "", res.title, flags=re.I).strip() or None
    if not ent.website:
        ent.website = res.url
    return ent


async def extract(text: str, image_b64: Optional[str], mime: Optional[str]) -> Entities:
    raw = await gemini.generate_json(EXTRACT_PROMPT + (text or "(see image)"), image_b64, mime)
    base = heuristic_entities(text)
    if not raw:
        return base
    try:
        ent = Entities(**{k: v for k, v in raw.items() if k in Entities.model_fields and v not in ("", "null")})
    except Exception:
        return base
    # fill gaps the model missed with regex results; regex always wins for payment demand
    for f in ("contact_email", "phone", "website", "product", "claimed_price", "claimed_original_price"):
        if not getattr(ent, f):
            setattr(ent, f, getattr(base, f))
    ent.payment_requested = ent.payment_requested or base.payment_requested
    return ent


def red_flags(text: str, ent: Entities) -> list:
    """Deterministic text-pattern checks: no network, no LLM."""
    out = []
    n = 0

    def add(title, detail, weight):
        nonlocal n
        n += 1
        out.append(Evidence(id=f"text-{n}", engine="text-analysis", title=title, detail=detail, signal="negative", weight=weight))

    if ent.payment_requested or FEE_RE.search(text):
        add("Asks you to pay money", "Genuine employers and sellers do not charge candidates a registration, training or security fee.", -30)
    if CHAT_ONLY_RE.search(text):
        add("Moves the conversation to WhatsApp/Telegram", "Scam offers push you to private chat apps where there is no paper trail.", -8)
    if URGENCY_RE.search(text):
        add("Artificial urgency", "Pressure to respond within hours is a standard manipulation tactic.", -10)
    if NO_INTERVIEW_RE.search(text):
        add("Selection without interview or experience", "Real hiring involves screening; guaranteed selection is a red flag.", -15)
    if UNREAL_PAY_RE.search(text):
        add("Unrealistic pay", "Pay claims far above market for the described work are typical bait.", -15)
    return out
