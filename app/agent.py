# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from pydantic import BaseModel, Field
import google.auth
from google.auth.exceptions import DefaultCredentialsError

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.models import Gemini
from google.adk.workflow import START, Workflow, node
from google.genai import types

# Safe GCP credential resolution for local development and testing
try:
    _, project_id = google.auth.default()
except (DefaultCredentialsError, Exception):
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "dummy-project")

os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

if os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
else:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True")


# Data Schemas
class ExpenseClaim(BaseModel):
    amount: float = Field(description="The amount of the expense claim in USD.")
    description: str = Field(description="A brief description of the expense item or service.")


class ExpenseReportResult(BaseModel):
    status: str = Field(description="The final status of the claim: APPROVED or REJECTED.")
    amount: float = Field(description="The claimed expense amount.")
    description: str = Field(description="The description of the expense.")
    reason: str = Field(description="The reason for the approval or rejection.")


# LLM Extractor Agent Node
extractor = LlmAgent(
    name="extractor",
    model=Gemini(model="gemini-2.5-flash"),
    instruction="""You are an expense extraction assistant.
Extract the expense details (amount in USD as a float, and description) from the user's message.
Provide the output in the requested JSON structure matching ExpenseClaim.
If the amount is not clear, output your best guess or standard amount.
If the description is not clear, summarize the input text.""",
    output_schema=ExpenseClaim,
)


# Routing Classifier Function
def classifier(node_input: ExpenseClaim) -> Event:
    if node_input.amount < 100.0:
        return Event(output=node_input, route="auto")
    else:
        return Event(output=node_input, route="review")


# Auto-Approve Node
@node(name="auto_approve")
def auto_approve(node_input: ExpenseClaim) -> Event:
    result = ExpenseReportResult(
        status="APPROVED",
        amount=node_input.amount,
        description=node_input.description,
        reason="Expense is under $100 and was automatically approved.",
    )
    return Event(
        output=result,
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text=f"✅ **Auto-Approved:** Claim of ${node_input.amount:.2f} for '{node_input.description}' has been approved automatically."
                )
            ],
        ),
    )


# Review Node (Human-in-the-Loop)
@node(name="review_agent", rerun_on_resume=True)
async def review_agent(ctx: Context, node_input: ExpenseClaim):
    if not ctx.resume_inputs or "approved" not in ctx.resume_inputs:
        yield RequestInput(
            interrupt_id="approved",
            message=f"Expense of ${node_input.amount:.2f} for '{node_input.description}' requires review. Do you approve? (yes/no)",
        )
        return

    val = ctx.resume_inputs["approved"]
    if isinstance(val, dict):
        decision = val.get("response") or val.get("output") or ""
    else:
        decision = str(val)
    
    decision = decision.strip().lower()
    is_approved = decision in ["yes", "y", "approve", "approved", "true"]
    
    status = "APPROVED" if is_approved else "REJECTED"
    reason = "Approved by manager via manual review." if is_approved else "Rejected by manager via manual review."
    
    result = ExpenseReportResult(
        status=status,
        amount=node_input.amount,
        description=node_input.description,
        reason=reason,
    )
    
    yield Event(
        output=result,
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text=f"✍️ **Manual Review Complete:** Claim for '{node_input.description}' of ${node_input.amount:.2f} has been **{status}**. Reason: {reason}"
                )
            ],
        ),
    )


# Workflow Definition
workflow_agent = Workflow(
    name="expense_workflow",
    edges=[
        (START, extractor),
        (extractor, classifier),
        (classifier, {"auto": auto_approve, "review": review_agent}),
    ],
    description="Ambient expense workflow that approves small claims or pauses for review of larger claims.",
    output_schema=ExpenseReportResult,
)

# App Configuration
app = App(
    root_agent=workflow_agent,
    name="app",
    resumability_config=ResumabilityConfig(is_resumable=True),
)

# Alias for backwards compatibility with test files
root_agent = workflow_agent


