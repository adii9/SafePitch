from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from safepitch.models import (
    create_dynamic_model,
    DiscrepancyAnalysis,
    StartupRating,
    FinalConsolidatedReport
)
import os

os.environ['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = "gemini/gemini-2.5-flash"

@CrewBase
class SafepitchCrew():
    """Safepitch Crew for automated Pitch Deck Intelligence"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self, client_schema: dict = None, *args, **kwargs):
        self.client_schema = client_schema or {}
        
        # Combine all dynamic fields (KYC, Financial, Market) into one model for extraction task
        all_fields = []
        all_fields.extend(self.client_schema.get('kyc', []))
        all_fields.extend(self.client_schema.get('financial', []))
        all_fields.extend(self.client_schema.get('market', []))

        self.ExtractionModel = create_dynamic_model('DeckExtractionData', all_fields)
        # We can reuse the same dynamically created model for verification, but add a field for sources?
        # Actually, for intermediate tasks it's okay to emit raw JSON, but defining the model ensures strictly structured data.
        # But for 'internet_verification_task', expected output includes sources array. Let's just output pure JSON.
        # The FinalConsolidationTask will enforce the FinalConsolidatedReport model.

    @agent
    def extraction_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['extraction_specialist'],
            llm=GEMINI_MODEL,
            verbose=True
        )

    @agent
    def osint_investigator(self) -> Agent:
        return Agent(
            config=self.agents_config['osint_investigator'],
            tools=[SerperDevTool()],
            llm=GEMINI_MODEL,
            verbose=True
        )

    @agent
    def risk_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['risk_analyst'],
            llm=GEMINI_MODEL,
            verbose=True
        )

    @agent
    def ic_scoring_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['ic_scoring_agent'],
            llm=GEMINI_MODEL,
            verbose=True
        )

    @task
    def pitch_deck_extraction_task(self) -> Task:
        return Task(
            config=self.tasks_config['pitch_deck_extraction_task'],
            output_json=self.ExtractionModel,
        )

    @task
    def internet_verification_task(self) -> Task:
        return Task(
            config=self.tasks_config['internet_verification_task'],
        )

    @task
    def discrepancy_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['discrepancy_analysis_task'],
            output_json=DiscrepancyAnalysis,
        )

    @task
    def startup_rating_task(self) -> Task:
        return Task(
            config=self.tasks_config['startup_rating_task'],
            output_json=StartupRating,
        )

    @task
    def final_consolidation_task(self) -> Task:
        return Task(
            config=self.tasks_config['final_consolidation_task'],
            output_json=FinalConsolidatedReport,
        )

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
