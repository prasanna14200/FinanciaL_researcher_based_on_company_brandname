"""Command-line entry point for the existing CrewAI workflow."""
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

from financial_researcher.crew import ResearchCrew


def run():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Research a selected company")
    parser.add_argument("company", help="Company or brand name")
    parser.add_argument("--identity-url", required=True, help="URL identifying the selected company")
    args = parser.parse_args()
    if not os.environ.get("HUGGINGFACE_API_KEY"):
        parser.error("HUGGINGFACE_API_KEY is required")
    if not os.environ.get("SERPER_API_KEY"):
        parser.error("SERPER_API_KEY is required")

    result = ResearchCrew().crew().kickoff(inputs={
        "company": args.company, "identity_url": args.identity_url
    })
    report = Path("output/report.md")
    report.parent.mkdir(exist_ok=True)
    report.write_text(result.raw, encoding="utf-8")
    print(result.raw)
    print(f"\nReport saved to {report}")


if __name__ == "__main__":
    run()
