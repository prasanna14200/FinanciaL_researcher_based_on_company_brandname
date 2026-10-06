# Financial research by company or brand

This project uses the existing CrewAI researcher and analyst. A visitor enters a company or brand, chooses the intended search result, and starts a live Serper search plus a Hugging Face Meta Llama report. The report is shown in the browser and can be downloaded as Markdown. Company selection matters for ambiguous names. Ticker and exchange are shown only for an exact match in the SEC's public company listing; otherwise they are unavailable. The agent's report is an unverified draft. A live Microsoft run generated some questionable figures despite source instructions, so check every figure against its cited page before use.

## Local setup

Use Python 3.10.16 (the project permits Python 3.10 through 3.13). From the repository root:

```bash
python -m venv .venv
# activate .venv for your shell
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in `HUGGINGFACE_API_KEY` and `SERPER_API_KEY`. Obtain the former from [Hugging Face access tokens](https://huggingface.co/settings/tokens) and the latter from the [Serper dashboard](https://serper.dev/). Keep `.env` private. The model configured in `src/financial_researcher/config/agents.yaml` is `huggingface/meta-llama/Llama-3.3-70B-Instruct:together`. The original Llama 3 8B model returned `model_not_supported` in a live run. Llama 3.1 8B made tool calls but returned an empty response before finishing. Llama 3.3 on Novita returned a server overload error. Check model access, inference credits, and any provider billing in your Hugging Face account before enabling a public service.

The app loads `.env` locally. Run:

```bash
python -m financial_researcher.web
```

Open `http://localhost:10000`. To run from the command line instead:

```bash
financial_researcher Microsoft --identity-url https://www.microsoft.com/
```

The CLI writes `output/report.md`. The web app holds jobs and reports in memory so a Render restart or redeploy removes them. It accepts one active research job at a time. Its `/health` endpoint checks that the web process is responsive; it does not check external API credentials.

## Render setup

Push these changes to the repository's `main` branch first. In Render, create **New > Web Service**, connect `https://github.com/prasanna14200/FinanciaL_researcher_based_on_company_brandname`, and use:

| Field | Value |
| --- | --- |
| Branch | `main` |
| Root Directory | leave blank |
| Runtime | Python 3 |
| Python version | `3.10.16` from `.python-version` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn financial_researcher.web:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120` |
| Health Check Path | `/health` |

Add `HUGGINGFACE_API_KEY` and `SERPER_API_KEY` on the service's **Environment** page. Render sets `PORT`; do not add it yourself. Start with a **Standard** instance (2 GB RAM) because CrewAI's tool dependencies are large and reports can run for minutes. Free and Starter offer 512 MB RAM and may fail from memory pressure; Free also sleeps after 15 minutes idle and loses in-memory reports. The process runs one worker. A request only starts a background thread; the browser polls for progress while the model runs. If the process restarts, the job disappears. This is suitable for small personal use, not durable or concurrent production workloads.

After deployment, open the Render URL, enter **Microsoft**, inspect the search links, select the Microsoft entity, start research, wait for completion, read the report, and download Markdown. Confirm the researcher used real sources and the report's factual claims cite valid URLs. If the service reports missing credentials, add the variables. If Hugging Face reports model access, quota, or provider errors, check token permissions, gated model access and available inference credits. If Render reports a worker timeout, check the logs and keep the browser job polling; if the process is killed for memory, select a larger instance. If search fails, check the Serper key and quota. If the build fails on a Python version, use the pinned `.python-version`.

The repository includes small model metadata and tokenizer files; it does not include model weights. The app uses Hugging Face inference and does not require a local model service. The committed `output/report.md` is a historical sample and is never shown as a new report.
