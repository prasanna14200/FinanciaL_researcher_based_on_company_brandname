# Financial Research CrewAI (Hugging Face API Version)

This project automates **financial research and reporting** using CrewAI with **Meta-LLaMA 3 via Hugging Face API**.

---

## Quick Setup

1. **Clone this repository**

```bash
git clone https://github.com/prasanna14200/FinanciaL_researcher_based_on_company_brandname.git
cd financial_researcher
Create a Python virtual environment

bash
Copy code
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux
Install dependencies

bash
Copy code
pip install -r requirements.txt
Create a Hugging Face account

Visit Hugging Face and generate an API token from Settings → Access Tokens.

bash
Copy code
HF_API_KEY=your_new_api_key_here
SERPER_API_KEY=your_serper_api_key  # optional, for web search
Run the Crew

bash
Copy code
python src/financial_researcher/main.py
The workflow automatically:

Researches the target company (research_task)

Generates a professional report (analysis_task)

Output report saved at: output/report.md, which includes:

Executive summary

Company overview

Financial performance

Challenges & opportunities

Recent news & market outlook

Notes

Note: Free-tier Hugging Face API has monthly limits. Upgrade or monitor usage if you hit "You have exceeded your monthly included credits" errors. Optionally, use Serper API for real-time web research.


Running the Project

To start your crew of AI agents and execute tasks:

crewai run


This initializes the financial_researcher Crew, assembling the agents and assigning tasks as defined in your configuration. By default, it generates a report.md file in the root folder with a research output on LLMs.

Understanding Your Crew

The financial_researcher Crew is composed of multiple AI agents, each with unique roles, goals, and tools. Agents collaborate on tasks defined in config/tasks.yaml, leveraging their collective skills. Agent configurations are outlined in config/agents.yaml.

Support

For support, questions, or feedback:

Documentation

GitHub Repository

Discord Community

Chat with Docs

Author: Prasanna
Email: prasannaprasanna14200@gmail.com

Date: 2025-10-15

Let's create wonders together with the power and simplicity of CrewAI.
