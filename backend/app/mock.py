"""Offline canned SerpApi responses so the whole pipeline can be tested without credits."""
from typing import Any, Dict

REAL = ("infosys", "tcs", "tata consultancy", "wipro")
REAL_DOMAINS = ("infosys.com", "tcs.com", "wipro.com")


def _is_real(q: str) -> bool:
    return any(r in q.lower() for r in REAL)


def serp(engine: str, params: Dict[str, Any]) -> Dict[str, Any]:
    q = params.get("q", "")
    real = _is_real(q)
    if engine == "google":
        if q.startswith('"') and q.endswith('"') and " " not in q:  # sender-domain lookup: only real domains are indexed
            d = q.strip('"').lower()
            if d in REAL_DOMAINS:
                return {"organic_results": [{"title": f"Contact | {d}", "link": f"https://www.{d}/contact", "snippet": f"Write to us at careers@{d}."}]}
            return {"organic_results": []}
        if q.startswith('"9123456780"'):  # phone lookup: this number has complaints
            return {"organic_results": [{"title": "9123456780 fraud - fake iPhone sale on WhatsApp", "link": "https://www.reddit.com/r/india/x",
                                         "snippet": "Paid advance to +91 91234 56780, never delivered. Scam."}]}
        if "scam" in q.lower() or "fraud" in q.lower():
            if real:
                return {"organic_results": [{
                    "title": "Beware of fake job offers sent in the name of Infosys",
                    "link": "https://www.infosys.com/careers/fraud-alert.html",
                    "snippet": "Infosys never asks candidates for money. Fake offers are circulating in the name of Infosys."}]}
            return {"organic_results": [
                {"title": "Zentrix Global Solutions - scam? complaints from students", "link": "https://www.quora.com/zentrix-scam",
                 "snippet": "Zentrix Global Solutions asked for a registration fee, it was a fraud."},
                {"title": "Zentrix Global fake internship offer - beware", "link": "https://www.reddit.com/r/developersIndia/zentrix",
                 "snippet": "Zentrix Global Solutions is a fake company, many complaints."},
                {"title": "Complaint against Zentrix Global Solutions", "link": "https://www.consumercomplaints.in/zentrix",
                 "snippet": "Cheated by Zentrix Global Solutions after paying training fee."}]}
        if real:
            return {"organic_results": [{"title": "Infosys | Digital Services and Consulting", "link": "https://www.infosys.com/", "snippet": "Infosys is a global leader."}]}
        return {"organic_results": [{"title": "Top IT companies in India", "link": "https://www.example-listing.in/top-it", "snippet": "A listing."}]}
    if engine == "google_news":
        if real:
            return {"news_results": [{"title": "Infosys warns of fake recruitment emails", "link": "https://news.example.com/a", "source": {"name": "Example News"}}]}
        return {"news_results": [{"title": "Police arrest gang running fake internship racket in the name of Zentrix Global", "link": "https://news.example.com/b", "source": {"name": "Example News"}}]}
    if engine == "google_maps":
        if real:
            return {"local_results": [{"title": "Infosys Limited", "address": "Electronics City, Hosur Road, Bengaluru, Karnataka", "rating": 4.1, "reviews": 9000,
                                       "type": "Software company", "website": "https://www.infosys.com/"}]}
        return {"local_results": []}
    if engine == "google_jobs":
        if real:
            return {"jobs_results": [{"title": "Software Engineer Trainee", "company_name": "Infosys", "via": "via Infosys Careers", "location": "Bengaluru"}]}
        return {"jobs_results": []}
    if engine == "google_shopping":
        return {"shopping_results": [{"title": "Sample phone", "extracted_price": 52000, "link": "https://shop.example.com/1", "source": "Shop"},
                                     {"title": "Sample phone", "extracted_price": 54000, "link": "https://shop.example.com/2", "source": "Shop2"},
                                     {"title": "Sample phone", "extracted_price": 56000, "link": "https://shop.example.com/3", "source": "Shop3"}]}
    if engine == "google_lens":
        return {"visual_matches": [{"title": f"Stock photo {i}", "link": f"https://site{i}.example.com/img", "source": f"site{i}"} for i in range(7)]}
    return {}
