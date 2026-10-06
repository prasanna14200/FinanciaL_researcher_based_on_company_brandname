# src/financial_researcher/crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
import os

@CrewBase
class ResearchCrew():
    """Research crew for comprehensive topic analysis and reporting"""

    @agent
    def researcher(self) -> Agent:
        if not os.environ.get("SERPER_API_KEY"):
            raise RuntimeError("SERPER_API_KEY is required for live research.")
        return Agent(
            config=self.agents_config['researcher'],
            verbose=True,
            max_iter=8,
            tools=[SerperDevTool(n_results=5)]
        )

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['analyst'],
            verbose=True,
            max_iter=4
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task']
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the research crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
