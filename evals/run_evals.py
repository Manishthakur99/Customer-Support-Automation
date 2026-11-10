from dataclasses import dataclass
import time

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_ai.exceptions import (
    ModelConnectionError,
    ModelOverloadedError,
    ModelRateLimitError,
    ModelServerError,
    ModelTimeoutError,
)

from app.ai.decide import decide
from app.ai.schemas import Decision
from evals.golden_emails import GOLDEN_EMAILS

RETRYABLE_ERRORS = (
    ModelConnectionError,
    ModelOverloadedError,
    ModelRateLimitError,
    ModelServerError,
    ModelTimeoutError,
)


@dataclass
class SectionMatches(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return ctx.output.section == ctx.expected_output["section"]


@dataclass
class ActionMatches(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return ctx.output.action == ctx.expected_output["action"]


def run_pipeline(email: str) -> Decision:
    for attempt in range(5):
        try:
            return decide(email)
        except RETRYABLE_ERRORS:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt * 2)
    raise RuntimeError("unreachable")


dataset = Dataset(
    name="golden-emails",
    cases=[
        Case(
            name=case["name"],
            inputs=case["email"],
            expected_output={"section": case["section"], "action": case["action"]},
        )
        for case in GOLDEN_EMAILS
    ],
    evaluators=[SectionMatches(), ActionMatches()],
)

if __name__ == "__main__":
    report = dataset.evaluate_sync(run_pipeline, max_concurrency=2)
    report.print(include_input=False, include_output=True, include_durations=False)