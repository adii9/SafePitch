from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from safepitch.models import VerificationReport, ErrorOutput, create_dynamic_model
import os

# Gemini configuration
os.environ['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '')

GEMINI_MODEL = "gemini/gemini-2.5-flash"

@CrewBase
class SafepitchCrew():
    """Safepitch Crew for automated Pitch Deck Auditing"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self, client_schema: dict = None, *args, **kwargs):
        self.client_schema = client_schema or {}
        
        # Dynamically create Pydantic models for each task
        self.KycModel = create_dynamic_model('KycData', self.client_schema.get('kyc', []))
        self.FinancialModel = create_dynamic_model('FinancialData', self.client_schema.get('financial', []))
        self.MarketModel = create_dynamic_model('MarketData', self.client_schema.get('market', []))

    @agent
    def kyc_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['kyc_specialist'],
            tools=[SerperDevTool()],
            llm=GEMINI_MODEL,
            verbose=True
        )

    @agent
    def financial_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config['financial_auditor'],
            llm=GEMINI_MODEL,
            verbose=True
        )

    @agent
    def market_intelligence_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['market_intelligence_analyst'],
            tools=[SerperDevTool()],
            llm=GEMINI_MODEL,
            verbose=True
        )

    # @agent
    # def claim_verification_specialist(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['claim_verification_specialist'],
    #         tools=[SerperDevTool()],
    #         llm=GEMINI_MODEL,
    #         verbose=True
    #     )

    @task
    def kyc_onboarding_task(self) -> Task:
        return Task(
            config=self.tasks_config['kyc_onboarding_task'],
            output_json=self.KycModel,
        )

    @task
    def financial_extraction_task(self) -> Task:
        return Task(
            config=self.tasks_config['financial_extraction_task'],
            output_json=self.FinancialModel,
        )

    @task
    def market_verification_task(self) -> Task:
        return Task(
            config=self.tasks_config['market_verification_task'],
            output_json=self.MarketModel,
        )

    # @task
    # def claim_verification_task(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['claim_verification_task'],
    #         context=[
    #             self.kyc_onboarding_task(),
    #             self.financial_extraction_task(),
    #             self.market_verification_task()
    #         ],
    #         output_json=VerificationReport,
    #     )

    # @task
    # def final_consolidation_task(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['final_consolidation_task'],
    #         context=[
    #             self.kyc_onboarding_task(),
    #             self.financial_extraction_task(),
    #             self.market_verification_task(),
    #             self.claim_verification_task()
    #         ],
    #         output_json=FinalAuditOutput,
    #     )

    @crew
    def crew(self) -> Crew:
        """Creates the Safepitch crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            tracing=True,
        )
