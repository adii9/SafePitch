from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
import os

@CrewBase
class SafepitchCrew():
    """Safepitch Crew for automated Pitch Deck Auditing"""

    # Path to your YAML configurations
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        # We ensure API keys are set for LiteLLM (which uses GEMINI_API_KEY)
        self.gemini_api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set")

        # Ensure GEMINI_API_KEY is explicitly set for LiteLLM to pick up automatically
        os.environ['GEMINI_API_KEY'] = self.gemini_api_key

    @agent
    def kyc_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['kyc_specialist'],
            tools=[SerperDevTool()], # Search for company incorporation/LinkedIn
            llm="gemini/gemini-2.5-flash",
            verbose=True
        )

    @agent
    def financial_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config['financial_auditor'],
            llm="gemini/gemini-2.5-flash",
            # No search tools here to ensure data only comes from the LlamaParsed markdown
            verbose=True
        )

    @agent
    def market_intelligence_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['market_intelligence_analyst'],
            llm="gemini/gemini-2.5-flash",
            tools=[SerperDevTool()], # Agent can now "read" Tracxn pages
            verbose=True
        )

    @task
    def kyc_onboarding_task(self) -> Task:
        return Task(
            config=self.tasks_config['kyc_onboarding_task'],
        )

    @task
    def financial_extraction_task(self) -> Task:
        return Task(
            config=self.tasks_config['financial_extraction_task'],
        )

    @task
    def market_verification_task(self) -> Task:
        return Task(
            config=self.tasks_config['market_verification_task'],
            # This task outputs the final JSON that n8n will read
            output_json=None
        )

    @task
    def final_consolidation_task(self) -> Task:
        return Task(
            config=self.tasks_config['final_consolidation_task'],
            context=[
                self.kyc_onboarding_task(),
                self.financial_extraction_task(),
                self.market_verification_task()
            ],
            output_json=None
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Safepitch crew"""
        return Crew(
            agents=self.agents, # Automatically collected by @agent decorator
            tasks=self.tasks,   # Automatically collected by @task decorator
            process=Process.sequential, # Important: Market analyst needs KYC/Financial context
            verbose=True,
        )