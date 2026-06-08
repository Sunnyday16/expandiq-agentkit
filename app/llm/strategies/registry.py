from app.llm.strategies.bad_email import BadEmailMockStrategy
from app.llm.strategies.base import MockStrategy
from app.llm.strategies.email import EmailMockStrategy
from app.llm.strategies.revenue_summary import RevenueSummaryMockStrategy
from app.llm.strategies.stuck import StuckMockStrategy
from app.llm.strategies.transient import TransientMockStrategy

MOCK_STRATEGIES: list[MockStrategy] = [
    StuckMockStrategy(),
    TransientMockStrategy(),
    BadEmailMockStrategy(),
    EmailMockStrategy(),
    RevenueSummaryMockStrategy(),
]
