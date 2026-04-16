from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
import os

# MiniMax OpenAI-compatible configuration
# Base URL: https://api.minimax.io/v1
# Model: MiniMax-M2.7
os.environ['OPENAI_API_BASE'] = os.environ.get('OPENAI_API_BASE', 'https://api.minimax.io/v1')
os.environ['OPENAI_API_KEY'] = os.environ.get('MINIMAX_API_KEY', '')

# Using openai/ prefix + OPENAI_API_BASE env var = litellm OpenAI-compatible handler
# This is the correct litellm format for custom OpenAI-compatible endpoints
MINIMAX_MODEL = "openai/MiniMax-M2.7"

@CrewBase
class SafepitchCrew():
    """Safepitch Crew for automated Pitch Deck Auditing"""

    # Path to your YAML configurations
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        # Ensure MiniMax is configured
        minimax_key = os.environ.get('MINIMAX_API_KEY') or os.environ.get('OPENAI_API_KEY', '')
        if minimax_key:
            os.environ['OPENAI_API_KEY'] = minimax_key
        os.environ['OPENAI_API_BASE'] = 'https://api.minimax.io/v1'

    @agent
    def kyc_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['kyc_specialist'],
            tools=[SerperDevTool()], # Search for company incorporation/LinkedIn
            llm=MINIMAX_MODEL,
            verbose=True
        )

    @agent
    def financial_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config['financial_auditor'],
            llm=MINIMAX_MODEL,
            # No search tools here to ensure data only comes from the LlamaParsed markdown
            verbose=True
        )

    @agent
    def market_intelligence_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['market_intelligence_analyst'],
            llm=MINIMAX_MODEL,
            tools=[SerperDevTool()], # Agent can now "read" Tracxn pages
            verbose=True
        )

    @agent
    def claim_verification_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['claim_verification_specialist'],
            tools=[SerperDevTool()],
            llm=MINIMAX_MODEL,
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
        )

    @task
    def claim_verification_task(self) -> Task:
        return Task(
            config=self.tasks_config['claim_verification_task'],
            context=[
                self.kyc_onboarding_task(),
                self.financial_extraction_task(),
                self.market_verification_task()
            ],
        )

    @task
    def final_consolidation_task(self) -> Task:
        return Task(
            config=self.tasks_config['final_consolidation_task'],
            context=[
                self.kyc_onboarding_task(),
                self.financial_extraction_task(),
                self.market_verification_task(),
                self.claim_verification_task()
            ],
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