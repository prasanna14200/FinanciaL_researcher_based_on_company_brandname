"""Small web front end for the existing CrewAI research crew."""
from datetime import datetime, timezone
from io import BytesIO
import os
import re
from threading import Lock, Thread
from urllib.parse import urlparse
from uuid import uuid4

from flask import Flask, abort, jsonify, render_template_string, request, send_file
from dotenv import load_dotenv
import requests

load_dotenv()
app = Flask(__name__)
choices = {}
jobs = {}
lock = Lock()
SEC_TICKERS = "https://www.sec.gov/files/company_tickers_exchange.json"

PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Financial Research</title>
<style>body{font:16px system-ui,sans-serif;max-width:850px;margin:2rem auto;padding:0 1rem;color:#17212b;background:#fafbfc}input,button{font:inherit;padding:.65rem}input{width:min(95%,480px)}button{cursor:pointer;background:#145da0;color:white;border:0;border-radius:4px}article{background:white;padding:1.25rem;margin:1rem 0;border:1px solid #ddd;border-radius:6px}label{display:block;margin:.6rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 system-ui}small{color:#4a5563}a{overflow-wrap:anywhere}</style>
<h1>Financial research</h1><p>Search for a company or brand, select the intended entity, then run the researcher and analyst.</p>
<form method="post" action="/resolve"><label for="company">Company or brand</label><input id="company" name="company" maxlength="100" required value="{{ query|default('') }}"> <button>Find company</button></form>
{% if error %}<article role="alert">{{ error }}</article>{% endif %}
{% if candidates %}<article><h2>Select the intended company</h2><p>Search results can include similarly named companies. Check the link before starting research. If your company is absent, search again using its full legal name or website name.</p>
{% for c in candidates %}<form method="post" action="/research"><input type="hidden" name="selection" value="{{ selection }}:{{ loop.index0 }}"><label><strong>{{ c.title }}</strong><br><a href="{{ c.link }}" target="_blank" rel="noopener">{{ c.link }}</a><br><small>{{ c.snippet }}</small></label><button>Research this entity</button></form>{% endfor %}</article>{% endif %}
{% if job %}<article><h2>Research progress</h2><p id="status">{{ job.status }}</p><div id="result"></div></article>
<script>const id={{ job.id|tojson }};async function poll(){try{const r=await fetch('/jobs/'+id);const j=await r.json();document.getElementById('status').textContent=j.status;if(j.status==='complete'){let e=document.getElementById('result');e.innerHTML='';let p=document.createElement('p');p.textContent='Selected entity: '+j.identified_as+' · Query: '+j.company+' · Ticker: '+(j.ticker||'unavailable')+' · Exchange: '+(j.exchange||'unavailable')+' · Report date: '+j.date;e.append(p);if(j.listing_source){let ls=document.createElement('a');ls.href=j.listing_source;ls.textContent='SEC listing source';ls.target='_blank';ls.rel='noopener';e.append(ls,document.createElement('br'))}let a=document.createElement('a');a.href='/jobs/'+id+'/download';a.textContent='Download Markdown report';e.append(a);let h=document.createElement('h3');h.textContent='Unverified agent report (check all figures and citations)';e.append(h);let pre=document.createElement('pre');pre.textContent=j.report;e.append(pre);let s=document.createElement('h3');s.textContent='Identity search source';e.append(s);let link=document.createElement('a');link.href=j.identity_url;link.textContent=j.identity_url;link.target='_blank';link.rel='noopener';e.append(link);let sh=document.createElement('h3');sh.textContent='Links cited by agents (unverified)';e.append(sh);if(!j.source_links.length){let x=document.createElement('p');x.textContent='No source links supplied by agents.';e.append(x)}for(const u of j.source_links){let l=document.createElement('a');l.href=u;l.textContent=u;l.target='_blank';l.rel='noopener';e.append(l,document.createElement('br'))}return}if(j.status==='failed'){document.getElementById('result').textContent=j.error;return}setTimeout(poll,3000)}catch(e){document.getElementById('status').textContent='Connection lost; retrying';setTimeout(poll,5000)}}poll();</script>{% endif %}
<p><small>Reports are unverified AI drafts. Financial amounts and citations have not been checked against the linked pages. Reports are held in memory and disappear when this service restarts.</small></p></html>"""


def search_company(name):
    key = os.environ.get("SERPER_API_KEY", "").strip().strip('"\'')
    if not key:
        raise RuntimeError("SERPER_API_KEY is missing. Add it in Render Environment.")
    if key.startswith("SERPER_API_KEY="):
        raise RuntimeError("The SERPER_API_KEY value must be the key alone, without SERPER_API_KEY=.")
    # CrewAI's Serper tool reads this same variable later in the job.
    os.environ["SERPER_API_KEY"] = key
    response = requests.post("https://google.serper.dev/search", headers={"X-API-KEY": key},
                             json={"q": f"{name} brand or company official website", "num": 8}, timeout=20)
    if response.status_code in (401, 403):
        raise RuntimeError(
            f"Serper rejected the search (HTTP {response.status_code}). In Render Environment, "
            "set SERPER_API_KEY to the raw active key from serper.dev (no name, quotes, or spaces), "
            "check that the account has search credits, then save and redeploy. No research was started."
        )
    if response.status_code == 429:
        raise RuntimeError("Serper rate limit reached (HTTP 429). Wait and try again or check the account limit.")
    response.raise_for_status()
    found = []
    for item in response.json().get("organic", []):
        url = item.get("link", "")
        if urlparse(url).scheme in ("http", "https"):
            found.append({"title": item.get("title", "Untitled"), "link": url,
                          "snippet": item.get("snippet", "")})
    if not found:
        raise RuntimeError("Search returned no company links. Try a more specific name.")
    return found


def _company_key(name):
    name = re.split(r"\s[|–-]\s", name, maxsplit=1)[0]
    words = re.findall(r"[a-z0-9]+", name.lower())
    while words and words[-1] in {"inc", "incorporated", "corp", "corporation", "company", "co", "ltd"}:
        words.pop()
    return " ".join(words)


def lookup_listing(query, selected_title, identity_url):
    """Return only exact SEC company-name matches; otherwise leave fields unknown."""
    try:
        response = requests.get(SEC_TICKERS, headers={"User-Agent":
            "FinancialResearcher prasannaprasanna14200@gmail.com"}, timeout=15)
        response.raise_for_status()
        data = response.json()["data"]
    except (requests.RequestException, ValueError, KeyError):
        return None
    selected = _company_key(selected_title)
    name = _company_key(query)
    matches = [row for row in data if _company_key(row[1]) == selected]
    host = urlparse(identity_url).hostname or ""
    query_in_host = name.replace(" ", "") in host.replace("-", "")
    if not matches and query_in_host and selected in {"home page", "official website", "official site", name}:
        matches = [row for row in data if _company_key(row[1]) == name]
    if len(matches) != 1:
        return None
    return {"ticker": matches[0][2], "exchange": matches[0][3], "source": SEC_TICKERS}


def run_research(job_id):
    job = jobs[job_id]
    try:
        job["status"] = "Researcher searching sources; analyst preparing report"
        from financial_researcher.crew import ResearchCrew
        result = ResearchCrew().crew().kickoff(inputs={"company": job["company"],
                                                 "identity_url": job["identity_url"]})
        report = (result.raw or "").strip()
        if not report:
            raise RuntimeError("The model returned an empty report.")
        job["report"] = report
        job["source_links"] = sorted({url.rstrip(".,;") for url in
            re.findall(r"https?://[^\s)\]>]+", report)})[:30]
        job["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")
        job["status"] = "complete"
    except Exception as exc:
        message = str(exc)
        for name in ("HUGGINGFACE_API_KEY", "SERPER_API_KEY"):
            secret = os.environ.get(name)
            if secret:
                message = message.replace(secret, "[redacted]")
        job["error"] = f"Research failed: {message}"
        job["status"] = "failed"


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/")
def index():
    return render_template_string(PAGE)


@app.post("/resolve")
def resolve():
    name = request.form.get("company", "").strip()
    if not name or len(name) > 100:
        return render_template_string(PAGE, error="Enter a company or brand name (up to 100 characters)."), 400
    try:
        candidates = search_company(name)
    except Exception as exc:
        return render_template_string(PAGE, query=name, error=str(exc)), 502
    selection = uuid4().hex
    with lock:
        if len(choices) > 50:
            choices.clear()
        choices[selection] = (name, candidates)
    return render_template_string(PAGE, query=name, candidates=candidates, selection=selection)


@app.post("/research")
def research():
    selection, sep, number = request.form.get("selection", "").partition(":")
    with lock:
        found = choices.pop(selection, None)
    if not sep or not found or not number.isdigit() or int(number) >= len(found[1]):
        return render_template_string(PAGE, error="Selection expired. Search again."), 400
    if not os.environ.get("HUGGINGFACE_API_KEY"):
        return render_template_string(PAGE, error="HUGGINGFACE_API_KEY is missing. Add it in Render Environment."), 503
    candidate = found[1][int(number)]
    listing = lookup_listing(found[0], candidate["title"], candidate["link"])
    job_id = uuid4().hex
    job = {"id": job_id, "company": found[0], "identified_as": candidate["title"], "identity_url": candidate["link"],
           "ticker": listing["ticker"] if listing else None,
           "exchange": listing["exchange"] if listing else None,
           "listing_source": listing["source"] if listing else None,
           "status": "queued", "error": None,
           "report": None, "date": None, "source_links": []}
    with lock:
        if any(item["status"] not in ("complete", "failed") for item in jobs.values()):
            return render_template_string(PAGE, error="The service is busy. Try again later."), 503
        if len(jobs) >= 10:
            jobs.pop(next(iter(jobs)))
        jobs[job_id] = job
    Thread(target=run_research, args=(job_id,), daemon=True).start()
    return render_template_string(PAGE, job=job)


@app.get("/jobs/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        abort(404)
    return jsonify(job)


@app.get("/jobs/<job_id>/download")
def download(job_id):
    job = jobs.get(job_id)
    if not job or job["status"] != "complete":
        abort(404)
    content = f"# Research: {job['company']}\n\nStatus: Unverified AI draft; check all figures and citations against the linked sources.\n\nReport date: {job['date']}\n\nSelected entity: {job['identified_as']} ({job['identity_url']})\n\nTicker: {job['ticker'] or 'unavailable'}; exchange: {job['exchange'] or 'unavailable'}\n\nSEC listing source: {job['listing_source'] or 'unavailable'}\n\n" + job["report"]
    return send_file(BytesIO(content.encode("utf-8")), mimetype="text/markdown",
                     as_attachment=True, download_name="financial-research.md")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
