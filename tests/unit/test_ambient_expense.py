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

import pytest
from google.adk.agents import LlmAgent
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.runners import InMemoryRunner
from google.genai import types

from app.agent import (
    ExpenseClaim,
    ExpenseReportResult,
    classifier,
    auto_approve,
    review_agent,
    app
)


def test_classifier() -> None:
    # under 100
    claim_small = ExpenseClaim(amount=50.0, description="team lunch")
    event_small = classifier(claim_small)
    assert event_small.actions.route == "auto"
    assert event_small.output == claim_small

    # exactly 100
    claim_border = ExpenseClaim(amount=100.0, description="conference ticket")
    event_border = classifier(claim_border)
    assert event_border.actions.route == "review"

    # over 100
    claim_large = ExpenseClaim(amount=150.0, description="flight ticket")
    event_large = classifier(claim_large)
    assert event_large.actions.route == "review"


def test_auto_approve() -> None:
    claim = ExpenseClaim(amount=45.50, description="software subscription")
    # Access the undecorated function via the node's private _func attribute
    event = auto_approve._func(claim)
    
    assert isinstance(event, Event)
    result = event.output
    assert isinstance(result, ExpenseReportResult)
    assert result.status == "APPROVED"
    assert result.amount == 45.50
    assert result.description == "software subscription"
    assert "automatically approved" in result.reason.lower()


@pytest.mark.asyncio
async def test_review_agent_needs_approval() -> None:
    claim = ExpenseClaim(amount=120.0, description="hotel stay")
    
    class MockContext:
        def __init__(self):
            self.resume_inputs = {}
            
    ctx = MockContext()
    
    events = []
    # Access the undecorated function via the node's private _func attribute
    async for event in review_agent._func(ctx, claim):
        events.append(event)
        
    assert len(events) == 1
    assert isinstance(events[0], RequestInput)
    assert events[0].interrupt_id == "approved"
    assert "requires review" in events[0].message


@pytest.mark.asyncio
async def test_review_agent_approved() -> None:
    claim = ExpenseClaim(amount=120.0, description="hotel stay")
    
    class MockContext:
        def __init__(self):
            self.resume_inputs = {"approved": "yes"}
            
    ctx = MockContext()
    
    events = []
    # Access the undecorated function via the node's private _func attribute
    async for event in review_agent._func(ctx, claim):
        events.append(event)
        
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    result = event.output
    assert isinstance(result, ExpenseReportResult)
    assert result.status == "APPROVED"
    assert "Approved by manager" in result.reason


@pytest.mark.asyncio
async def test_review_agent_rejected() -> None:
    claim = ExpenseClaim(amount=120.0, description="hotel stay")
    
    class MockContext:
        def __init__(self):
            self.resume_inputs = {"approved": "no"}
            
    ctx = MockContext()
    
    events = []
    # Access the undecorated function via the node's private _func attribute
    async for event in review_agent._func(ctx, claim):
        events.append(event)
        
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    result = event.output
    assert isinstance(result, ExpenseReportResult)
    assert result.status == "REJECTED"
    assert "Rejected by manager" in result.reason


@pytest.mark.asyncio
async def test_workflow_e2e_auto(monkeypatch) -> None:
    # Mock the LlmAgent class run_async
    async def mock_run_async(self, ctx):
        yield Event(output=ExpenseClaim(amount=45.0, description="lunch"))

    monkeypatch.setattr(LlmAgent, "run_async", mock_run_async)

    runner = InMemoryRunner(app=app)
    session = await runner.session_service.create_session(
        app_name="app", user_id="test_user"
    )
    
    message = types.Content(role="user", parts=[types.Part.from_text(text="I spent 45 on lunch")])
    
    events = []
    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=message,
    ):
        events.append(event)
        
    final_output = None
    for event in events:
        if isinstance(event.output, ExpenseReportResult):
            final_output = event.output
            
    assert final_output is not None
    # Output schema is ExpenseReportResult, so access it as an object
    assert final_output.status == "APPROVED"
    assert final_output.amount == 45.0
    assert final_output.description == "lunch"


@pytest.mark.asyncio
async def test_workflow_e2e_review_flow(monkeypatch) -> None:
    # Mock the LlmAgent class run_async
    async def mock_run_async(self, ctx):
        yield Event(output=ExpenseClaim(amount=150.0, description="flights"))

    monkeypatch.setattr(LlmAgent, "run_async", mock_run_async)

    runner = InMemoryRunner(app=app)
    session = await runner.session_service.create_session(
        app_name="app", user_id="test_user"
    )
    
    message = types.Content(role="user", parts=[types.Part.from_text(text="I spent 150 on flights")])
    
    # 1. Run the workflow. It should stop and yield a RequestInput event.
    events = []
    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=message,
    ):
        events.append(event)
        
    # Verify we hit the interrupt by finding the adk_request_input function call
    request_input_events = []
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call and part.function_call.name == "adk_request_input":
                    request_input_events.append(part.function_call)
                    
    assert len(request_input_events) == 1
    assert request_input_events[0].id == "approved"
    
    # Check no final result output was produced yet
    outputs = [e.output for e in events if isinstance(e.output, ExpenseReportResult)]
    assert len(outputs) == 0
    
    # 2. Resume the session with approval
    resume_message = types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    name="adk_request_input",
                    id="approved",
                    response={"response": "yes"},
                )
            )
        ],
    )
    resume_events = []
    
    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=resume_message,
    ):
        resume_events.append(event)
        
    final_output = None
    for event in resume_events:
        if isinstance(event.output, ExpenseReportResult):
            final_output = event.output
            
    assert final_output is not None
    assert final_output.status == "APPROVED"
    assert final_output.amount == 150.0
    assert final_output.description == "flights"
    assert "Approved by manager" in final_output.reason
