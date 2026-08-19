import pytest
from app.services.ai.FieldOpsAI.agents.personalization import (
    PersonalizationAIError,
    PersonalizationPipeline,
    UnresolvedPlaceholderError,
)


class FakeGroqClient:
    def generate_result(self, **kwargs):
        prompt = kwargs["messages"][0]["content"]

        class FakeResult:
            text = prompt.split("MESSAGE:", 1)[-1].strip()

        return FakeResult()

def test_ai_enhancement_preserves_and_replaces_placeholders():
    pipeline = PersonalizationPipeline(
        groq_client=FakeGroqClient()
    )

    context = {
        "customer_name": "Alice",
        "job_title": "AC Repair",
    }

    result = pipeline.ai_enhance(
        context=context,
        template=(
            "Hello {{ customer.name }}, "
            "your {{ job.title }} is scheduled."
        ),
    )

    assert "Alice" in result
    assert "AC Repair" in result
    assert "pf_customer_name" not in result
    assert "pf_job_title" not in result

def test_replace_placeholders_locally():
    pipeline = PersonalizationPipeline()

    result = pipeline.replace_placeholders(
        "Hello {{ customer.name }}, your {{ job.title }} is ready.",
        {
            "customer_name": "Alice",
            "job_title": "AC Repair",
        },
    )

    assert result == "Hello Alice, your AC Repair is ready."

def test_communication_agent_personalizes_template():
    from app.services.ai.FieldOpsAI.agents.communication_agent import (
        CommunicationAgent,
    )
    from app.services.ai.FieldOpsAI.schemas.agent_config import AgentConfig
    from app.services.ai.FieldOpsAI.schemas.ai_task import AITask
    from app.services.ai.FieldOpsAI.schemas.communication import (
        CommunicationContext,
    )

    class FakePipeline:
        def ai_enhance(self, context, template):
            return "Hello Alice, your AC Repair is scheduled."

    config = AgentConfig(
        agent_type=AITask.COMMUNICATION,
        tenant_id="test-tenant",
    )

    agent = CommunicationAgent(
        config=config,
        personalization_pipeline=FakePipeline(),
    )

    assert agent.personalization_pipeline is not None

def test_communication_agent_uses_personalization_pipeline():
    from unittest.mock import Mock

    from app.services.ai.FieldOpsAI.agents.communication_agent import (
        CommunicationAgent,
    )
    from app.services.ai.FieldOpsAI.schemas.agent_config import AgentConfig
    from app.services.ai.FieldOpsAI.schemas.ai_task import AITask
    from app.services.ai.FieldOpsAI.schemas.communication import (
        CommunicationContext,
    )

    fake_pipeline = Mock()
    fake_pipeline.apply_template.return_value = (
        "Hello Alice, your AC Repair is scheduled."
    )

    config = AgentConfig(
        agent_type=AITask.COMMUNICATION,
        tenant_id="test-tenant",
    )

    agent = CommunicationAgent(
        config=config,
        personalization_pipeline=fake_pipeline,
    )

    context = CommunicationContext(
        job_id="job-1",
        correlation_id="test-1",
        notification_type="job_update",
        recipient_type="CUSTOMER",
        channel="SMS",
        customer_name="Alice",
        job_title="AC Repair",
        job_status="ASSIGNED",
        template=(
            "Hello {{ customer.name }}, "
            "your {{ job.title }} is scheduled."
        ),
        personalization_data={
            "customer": {
                "name": "Alice",
            },
            "job": {
                "title": "AC Repair",
            },
        },
    )

    assert agent.personalization_pipeline is fake_pipeline

@pytest.mark.asyncio
async def test_communication_agent_run_personalizes_before_orchestrator():
    from unittest.mock import Mock

    from app.services.ai.FieldOpsAI.agents.communication_agent import (
        CommunicationAgent,
    )
    from app.services.ai.FieldOpsAI.schemas.agent_config import AgentConfig
    from app.services.ai.FieldOpsAI.schemas.ai_task import AITask
    from app.services.ai.FieldOpsAI.schemas.communication import (
        CommunicationContext,
        CommunicationDecision,
    )

    fake_pipeline = Mock()
    fake_pipeline.ai_enhance.return_value = (
    "Hello Alice, your AC Repair is scheduled."
     )

    fake_orchestrator = Mock()

    fake_decision = Mock(spec=CommunicationDecision)
    fake_orchestrator.execute.return_value = fake_decision

    config = AgentConfig(
        agent_type=AITask.COMMUNICATION,
        tenant_id="test-tenant",
    )

    agent = CommunicationAgent(
        config=config,
        orchestrator=fake_orchestrator,
        personalization_pipeline=fake_pipeline,
    )

    context = CommunicationContext(
        job_id="job-1",
        correlation_id="test-1",
        notification_type="job_update",
        recipient_type="CUSTOMER",
        channel="SMS",
        customer_name="Alice",
        job_title="AC Repair",
        job_status="ASSIGNED",
        template=(
            "Hello {{ customer.name }}, "
            "your {{ job.title }} is scheduled."
        ),
        personalization_data={
            "customer": {
                "name": "Alice",
            },
            "job": {
                "title": "AC Repair",
            },
        },
    )

    result = await agent.run(
        context.model_dump(mode="json")
    )

    assert result is fake_decision

    fake_pipeline.ai_enhance.assert_called_once()

    call_kwargs = fake_pipeline.ai_enhance.call_args.kwargs

    assert call_kwargs["template"] == context.template
    assert call_kwargs["context"]["customer"]["name"] == "Alice"
    assert call_kwargs["context"]["job"]["title"] == "AC Repair"

    fake_orchestrator.execute.assert_called_once()

def test_nested_variables_render_correctly():
    pipeline = PersonalizationPipeline()

    result = pipeline.apply_template(
        "Service location: {{ customer.address.city }}",
        {
            "customer": {
                "name": "Alice",
                "address": {
                    "city": "Chennai",
                },
            },
        },
    )

    assert result == "Service location: Chennai"

def test_conditional_block_renders_when_data_exists():
    pipeline = PersonalizationPipeline()

    result = pipeline.apply_template(
        "{% if technician.name %}"
        "Technician: {{ technician.name }}"
        "{% endif %}",
        {
            "technician": {
                "name": "John",
            },
        },
    )

    assert result == "Technician: John"

def test_jinja_filters_render_correctly():
    from datetime import datetime

    pipeline = PersonalizationPipeline()

    result = pipeline.apply_template(
        (
            "{{ amount | currency }} | "
            "{{ name | title_case }} | "
            "{{ name | upper }} | "
            "{{ appointment | format_time }}"
        ),
        {
            "amount": 12345.5,
            "name": "alice johnson",
            "appointment": datetime(2026, 8, 17, 14, 30, 45),
        },
    )

    assert result == (
        "₹12,345.50 | "
        "Alice Johnson | "
        "ALICE JOHNSON | "
        "14:30:45"
    )

import pytest

from app.services.ai.FieldOpsAI.agents.personalization import (
    PersonalizationError,
)


def test_missing_variable_handling():
    pipeline = PersonalizationPipeline(
        optional_variables={"customer.phone"},
    )

    optional_result = pipeline.apply_template(
        "Phone: {{ customer.phone }}",
        {},
    )

    assert optional_result == "Phone: "

    with pytest.raises(
        PersonalizationError,
        match="Missing required path: customer.name",
    ):
        pipeline.apply_template(
            "Hello {{ customer.name }}",
            {},
        )

def test_ai_prompt_does_not_expose_real_customer_data():
    captured = {}

    class CapturingGroqClient:
        def generate_result(self, **kwargs):
            captured["messages"] = kwargs["messages"]

            class FakeResult:
                text = "Hello {{customer_name}}"

            return FakeResult()

    pipeline = PersonalizationPipeline(
        groq_client=CapturingGroqClient()
    )

    result = pipeline.ai_enhance(
        context={
            "customer_name": "Alice Johnson",
            "job_title": "AC Repair",
        },
        template="Hello {{ customer.name }}",
    )

    prompt = captured["messages"][0]["content"]

    assert "Alice Johnson" not in prompt
    assert "AC Repair" not in prompt
    assert "customer_name" in prompt
    assert "Alice Johnson" in result

def test_resolve_variables_from_db(monkeypatch):
    from unittest.mock import Mock

    from app.services.ai.FieldOpsAI.agents.personalization import (
        PersonalizationPipeline,
    )

    class FakeJob:
        id = "job-1"
        service_type = "AC Repair"
        issue_description = "AC not cooling"
        status = "ASSIGNED"
        customer_id = "customer-1"
        customer_name = "Alice"
        site_address = "Chennai"
        assigned_technician_id = "tech-1"

    class FakeTechnician:
        technician_id = "tech-1"
        technician_name = "John"
        technician_status = "AVAILABLE"
        technician_location = "Chennai"

    class FakeQuery:
        def __init__(self, model):
            self.model = model

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            if self.model is FakeJob:
                return FakeJob()
            if self.model is FakeTechnician:
                return FakeTechnician()
            return None

    class FakeDB:
        def query(self, model):
            return FakeQuery(model)

    import app.models as models

    monkeypatch.setattr(models, "Job", FakeJob)
    monkeypatch.setattr(models, "Technician", FakeTechnician)

    pipeline = PersonalizationPipeline(
        db=FakeDB()
    )

    result = pipeline.resolve_variables(
        {
            "job_id": "job-1",
        }
    )

    assert result["job"]["title"] == "AC Repair"
    assert result["job"]["status"] == "ASSIGNED"
    assert result["job"]["customer_id"] == "customer-1"
    assert result["job"]["customer_name"] == "Alice"
    assert result["job"]["address"]["full"] == "Chennai"

    assert result["customer"]["name"] == "Alice"

    assert result["technician"]["name"] == "John"
    assert result["technician"]["status"] == "AVAILABLE"
    assert result["technician"]["location"] == "Chennai"

    assert result["customer_name"] == "Alice"
    assert result["customer_id"] == "customer-1"
    assert result["technician_name"] == "John"

def test_resolve_variables_db_failure_returns_personalization_error():
    from unittest.mock import Mock

    from app.services.ai.FieldOpsAI.agents.personalization import (
        PersonalizationPipeline,
        PersonalizationVariableError,
    )

    class BrokenDB:
        def query(self, model):
            raise RuntimeError("database failure")

    pipeline = PersonalizationPipeline(
        db=BrokenDB()
    )

    with pytest.raises(
        PersonalizationVariableError,
        match="Unable to resolve job or technician",
    ):
        pipeline.resolve_variables(
            {
                "job_id": "job-1",
            }
        )

def test_ai_enhance_raises_when_groq_fails():
    class BrokenGroqClient:
        def generate_result(self, **kwargs):
            raise RuntimeError("Groq failed")

    pipeline = PersonalizationPipeline(
        groq_client=BrokenGroqClient()
    )

    with pytest.raises(
        PersonalizationAIError,
        match="AI personalization failed",
    ):
        pipeline.ai_enhance(
            context={
                "customer_name": "Alice",
            },
            template="Hello {{ customer.name }}",
        )


def test_ai_enhance_raises_for_empty_ai_response():
    class EmptyGroqClient:
        def generate_result(self, **kwargs):
            class Result:
                text = ""

            return Result()

    pipeline = PersonalizationPipeline(
        groq_client=EmptyGroqClient()
    )

    with pytest.raises(
        PersonalizationAIError,
        match="empty personalization response",
    ):
        pipeline.ai_enhance(
            context={
                "customer_name": "Alice",
            },
            template="Hello {{ customer.name }}",
        )


def test_ai_enhance_raises_for_unresolved_placeholder():
    class BadGroqClient:
        def generate_result(self, **kwargs):
            class Result:
                text = "Hello {{unknown_name}}"

            return Result()

    pipeline = PersonalizationPipeline(
        groq_client=BadGroqClient()
    )

    with pytest.raises(
        UnresolvedPlaceholderError,
        match="unresolved placeholders",
    ):
        pipeline.ai_enhance(
            context={
                "customer_name": "Alice",
            },
            template="Hello {{ customer.name }}",
        )


def test_ai_enhance_rejects_oversized_ai_response():
    class LargeGroqClient:
        def generate_result(self, **kwargs):
            class Result:
                text = "A" * (
                    PersonalizationPipeline.MAX_AI_OUTPUT_LENGTH + 1
                )

            return Result()

    pipeline = PersonalizationPipeline(
        groq_client=LargeGroqClient()
    )

    with pytest.raises(
        PersonalizationAIError,
        match="too long",
    ):
        pipeline.ai_enhance(
            context={
                "customer_name": "Alice",
            },
            template="Hello {{ customer.name }}",
        )

def test_plain_structure_supports_pydantic_model():
    from pydantic import BaseModel

    class Customer(BaseModel):
        name: str
        city: str

    pipeline = PersonalizationPipeline()

    result = pipeline._to_plain_structure(
        Customer(
            name="Alice",
            city="Chennai",
        )
    )

    assert result == {
        "name": "Alice",
        "city": "Chennai",
    }

from app.services.ai.FieldOpsAI.agents.personalization import (
    PersonalizationVariableError,
)

def test_plain_structure_rejects_unsupported_value():
    pipeline = PersonalizationPipeline()

    class Unsupported:
        pass

    with pytest.raises(
        PersonalizationVariableError,
        match="Unsupported personalization value type",
    ):
        pipeline._to_plain_structure(
            Unsupported()
        )


def test_plain_structure_handles_nested_collections():
    pipeline = PersonalizationPipeline()

    result = pipeline._to_plain_structure(
        {
            "customer": {
                "name": "Alice",
                "tags": [
                    "priority",
                    "premium",
                ],
            },
            "jobs": (
                "job-1",
                "job-2",
            ),
        }
    )

    assert result["customer"]["name"] == "Alice"
    assert result["customer"]["tags"] == [
        "priority",
        "premium",
    ]
    assert result["jobs"] == [
        "job-1",
        "job-2",
    ]

def test_plain_structure_handles_sqlalchemy_columns_and_loaded_relationships(
    monkeypatch,
):
    import app.services.ai.FieldOpsAI.agents.personalization as personalization

    pipeline = PersonalizationPipeline()

    class FakeColumn:
        def __init__(self, key):
            self.key = key

    class FakeRelationship:
        def __init__(self, key):
            self.key = key

    class FakeMapper:
        column_attrs = [
            FakeColumn("name"),
            FakeColumn("city"),
        ]

        relationships = [
            FakeRelationship("customer"),
        ]

    class FakeAttributeState:
        def __init__(self, value):
            self.loaded_value = value

    class FakeAttrs:
        customer = FakeAttributeState(
            {
                "name": "Alice",
            }
        )

        def __getitem__(self, key):
            return getattr(self, key)

    class FakeState:
        mapper = FakeMapper()
        attrs = FakeAttrs()

    class FakeCustomer:
        name = "Alice"

    class FakeORMObject:
        name = "John"
        city = "Chennai"
        customer = FakeCustomer()

    monkeypatch.setattr(
        personalization,
        "sqlalchemy_inspect",
        lambda value: FakeState(),
    )

    result = pipeline._to_plain_structure(
        FakeORMObject()
    )

    assert result["name"] == "John"
    assert result["city"] == "Chennai"
    assert result["customer"]["name"] == "Alice"

def test_plain_structure_skips_unloaded_sqlalchemy_relationship(
    monkeypatch,
):
    import app.services.ai.FieldOpsAI.agents.personalization as personalization

    pipeline = PersonalizationPipeline()

    class FakeColumn:
        key = "name"

    class FakeRelationship:
        key = "customer"

    class FakeMapper:
        column_attrs = [FakeColumn()]
        relationships = [FakeRelationship()]

    class FakeAttributeState:
        loaded_value = personalization.NO_VALUE

    class FakeAttrs:
        def __getitem__(self, key):
            return FakeAttributeState()

    class FakeState:
        mapper = FakeMapper()
        attrs = FakeAttrs()

    class FakeORMObject:
        name = "John"

    monkeypatch.setattr(
        personalization,
        "sqlalchemy_inspect",
        lambda value: FakeState(),
    )

    result = pipeline._to_plain_structure(
        FakeORMObject()
    )

    assert result == {
        "name": "John",
    }

    assert "customer" not in result

def test_apply_template_rejects_non_string_template():
    pipeline = PersonalizationPipeline()

    with pytest.raises(
        PersonalizationError,
        match="Template must be a string",
    ):
        pipeline.apply_template(
            template=None,
            variables={},
        )


def test_apply_template_rejects_oversized_template():
    pipeline = PersonalizationPipeline()

    oversized_template = (
        "A" * (PersonalizationPipeline.MAX_TEMPLATE_LENGTH + 1)
    )

    with pytest.raises(
        PersonalizationError,
        match="Template exceeds maximum allowed length",
    ):
        pipeline.apply_template(
            template=oversized_template,
            variables={},
        )


def test_apply_template_rejects_variable_injection_error(
    monkeypatch,
):
    from app.services.ai.FieldOpsAI.agents.personalization import (
        PromptVariableInjectionError,
    )

    pipeline = PersonalizationPipeline()

    def broken_render(**kwargs):
        raise PromptVariableInjectionError(
            "template variable injection failed"
        )

    monkeypatch.setattr(
        pipeline.injector,
        "render",
        broken_render,
    )

    with pytest.raises(
        PersonalizationError,
        match="template variable injection failed",
    ):
        pipeline.apply_template(
            "Hello {{ customer.name }}",
            {
                "customer_name": "Alice",
            },
        )


def test_apply_template_rejects_invalid_rendered_output(
    monkeypatch,
):
    class InvalidResult:
        rendered_body = None

    def invalid_render(**kwargs):
        return InvalidResult()

    pipeline = PersonalizationPipeline()

    monkeypatch.setattr(
        pipeline.injector,
        "render",
        invalid_render,
    )

    with pytest.raises(
        PersonalizationError,
        match="Template rendering returned invalid output",
    ):
        pipeline.apply_template(
            "Hello {{ customer.name }}",
            {
                "customer_name": "Alice",
            },
        )

def test_ai_enhance_raises_when_context_sanitization_fails(
    monkeypatch,
):
    pipeline = PersonalizationPipeline()

    def broken_sanitize(context):
        raise RuntimeError("sanitizer failed")

    monkeypatch.setattr(
        pipeline.sanitizer,
        "sanitize",
        broken_sanitize,
    )

    with pytest.raises(
        PersonalizationAIError,
        match="Unable to sanitize personalization context",
    ):
        pipeline.ai_enhance(
            context={
                "customer_name": "Alice",
            },
            template="Hello {{ customer.name }}",
        )


def test_ai_enhance_clears_placeholder_map_when_template_rendering_fails(
    monkeypatch,
):
    pipeline = PersonalizationPipeline()

    def broken_apply_template(*args, **kwargs):
        raise PersonalizationError(
            "template rendering failed"
        )

    monkeypatch.setattr(
        pipeline,
        "apply_template",
        broken_apply_template,
    )

    with pytest.raises(
        PersonalizationError,
        match="template rendering failed",
    ):
        pipeline.ai_enhance(
            context={
                "customer_name": "Alice",
            },
            template="Hello {{ customer.name }}",
        )


def test_ai_enhance_raises_when_prompt_sanitization_fails(
    monkeypatch,
):
    pipeline = PersonalizationPipeline()

    def broken_sanitize_prompt(
        prompt,
        placeholder_map,
    ):
        raise RuntimeError("prompt sanitizer failed")

    monkeypatch.setattr(
        pipeline.sanitizer,
        "sanitize_prompt",
        broken_sanitize_prompt,
    )

    with pytest.raises(
        PersonalizationAIError,
        match="Unable to safely prepare the AI prompt",
    ):
        pipeline.ai_enhance(
            context={
                "customer_name": "Alice",
            },
            template="Hello {{ customer.name }}",
        )

def test_ai_enhance_raises_when_restore_data_fails(
    monkeypatch,
):
    pipeline = PersonalizationPipeline()

    def broken_restore(*args, **kwargs):
        raise RuntimeError("restore failed")

    monkeypatch.setattr(
        pipeline.sanitizer,
        "restore_data",
        broken_restore,
    )

    class FakeGroqClient:
        def generate_result(self, **kwargs):
            class Result:
                text = "Hello {{customer_name}}"

            return Result()

    pipeline.groq_client = FakeGroqClient()

    with pytest.raises(
        PersonalizationAIError,
        match="Unable to restore personalized values",
    ):
        pipeline.ai_enhance(
            context={
                "customer_name": "Alice",
            },
            template="Hello {{ customer.name }}",
        )


def test_ai_enhance_rejects_non_string_restored_value(
    monkeypatch,
):
    pipeline = PersonalizationPipeline()

    monkeypatch.setattr(
        pipeline.sanitizer,
        "restore_data",
        lambda *args, **kwargs: None,
    )

    class FakeGroqClient:
        def generate_result(self, **kwargs):
            class Result:
                text = "Hello {{customer_name}}"

            return Result()

    pipeline.groq_client = FakeGroqClient()

    with pytest.raises(
        PersonalizationAIError,
        match="Restored AI response is not text",
    ):
        pipeline.ai_enhance(
            context={
                "customer_name": "Alice",
            },
            template="Hello {{ customer.name }}",
        )


def test_replace_placeholders_rejects_non_string_ai_text():
    pipeline = PersonalizationPipeline()

    with pytest.raises(
        PersonalizationError,
        match="AI text must be a string",
    ):
        pipeline.replace_placeholders(
            ai_text=None,
            real_data={
                "customer_name": "Alice",
            },
        )


def test_replace_placeholders_raises_when_sanitization_fails(
    monkeypatch,
):
    pipeline = PersonalizationPipeline()

    def broken_sanitize(*args, **kwargs):
        raise RuntimeError("sanitize failed")

    monkeypatch.setattr(
        pipeline.sanitizer,
        "sanitize",
        broken_sanitize,
    )

    with pytest.raises(
        PersonalizationError,
        match="Unable to restore personalization placeholders",
    ):
        pipeline.replace_placeholders(
            ai_text="Hello {{customer_name}}",
            real_data={
                "customer_name": "Alice",
            },
        )


def test_replace_placeholders_raises_on_injection_error(
    monkeypatch,
):
    from app.services.ai.FieldOpsAI.agents.personalization import (
        PromptVariableInjectionError,
    )

    pipeline = PersonalizationPipeline()

    def broken_render(**kwargs):
        raise PromptVariableInjectionError(
            "placeholder rendering failed"
        )

    monkeypatch.setattr(
        pipeline.injector,
        "render",
        broken_render,
    )

    with pytest.raises(
        PersonalizationError,
        match="placeholder rendering failed",
    ):
        pipeline.replace_placeholders(
            "Hello {{ customer.name }}",
            {
                "customer_name": "Alice",
            },
        )

def test_build_declarations_raises_on_injection_error(
    monkeypatch,
):
    pipeline = PersonalizationPipeline()

    from app.services.ai.FieldOpsAI.agents.personalization import (
        PromptVariableInjectionError,
    )

    def broken_infer(*args, **kwargs):
        raise PromptVariableInjectionError(
            "declaration inference failed"
        )

    monkeypatch.setattr(
        pipeline.injector,
        "infer_declarations",
        broken_infer,
    )

    with pytest.raises(
        PersonalizationError,
        match="declaration inference failed",
    ):
        pipeline._build_declarations(
            "Hello {{ customer.name }}"
        )


def test_pipeline_rejects_variable_both_optional_and_required():
    with pytest.raises(
        ValueError,
        match="A variable cannot be both optional and required",
    ):
        PersonalizationPipeline(
            optional_variables={"customer.name"},
            required_variables={"customer.name"},
        )

def test_normalize_path_rejects_non_string():
    with pytest.raises(
        ValueError,
        match="Variable path must be a string",
    ):
        PersonalizationPipeline._normalize_path(None)


def test_normalize_path_rejects_empty_path():
    with pytest.raises(
        ValueError,
        match="Variable path cannot be empty",
    ):
        PersonalizationPipeline._normalize_path("   ")


def test_matches_requirement_supports_parent_path():
    assert PersonalizationPipeline._matches_requirement(
        "customer.address.city",
        {"customer.address"},
    )

    assert not PersonalizationPipeline._matches_requirement(
        "customer.phone",
        {"customer.address"},
    )


def test_plain_structure_handles_sqlalchemy_column_getattr_failure(
    monkeypatch,
):
    import app.services.ai.FieldOpsAI.agents.personalization as personalization

    pipeline = PersonalizationPipeline()

    class FakeColumn:
        key = "name"

    class FakeMapper:
        column_attrs = [FakeColumn()]
        relationships = []

    class FakeState:
        mapper = FakeMapper()

    class FakeORMObject:
        pass

    monkeypatch.setattr(
        personalization,
        "sqlalchemy_inspect",
        lambda value: FakeState(),
    )

    def broken_getattr(obj, key):
        raise RuntimeError("column access failed")

    monkeypatch.setattr(
        personalization,
        "getattr",
        broken_getattr,
        raising=False,
    )

    with pytest.raises(
        PersonalizationVariableError,
        match="Unsupported personalization value type",
    ):
        pipeline._to_plain_structure(
            FakeORMObject()
        )


def test_plain_structure_handles_sqlalchemy_relationship_exception(
    monkeypatch,
):
    import app.services.ai.FieldOpsAI.agents.personalization as personalization

    pipeline = PersonalizationPipeline()

    class FakeRelationship:
        key = "customer"

    class FakeMapper:
        column_attrs = []
        relationships = [FakeRelationship()]

    class FakeAttrs:
        def __getitem__(self, key):
            raise RuntimeError("relationship access failed")

    class FakeState:
        mapper = FakeMapper()
        attrs = FakeAttrs()

    class FakeORMObject:
        pass

    monkeypatch.setattr(
        personalization,
        "sqlalchemy_inspect",
        lambda value: FakeState(),
    )

    with pytest.raises(
        PersonalizationVariableError,
        match="Unsupported personalization value type",
    ):
        pipeline._to_plain_structure(
            FakeORMObject()
        )


def test_plain_structure_handles_sqlalchemy_inspection_failure(
    monkeypatch,
):
    import app.services.ai.FieldOpsAI.agents.personalization as personalization

    pipeline = PersonalizationPipeline()

    class FakeORMObject:
        pass

    def broken_inspect(value):
        raise RuntimeError("inspection failed")

    monkeypatch.setattr(
        personalization,
        "sqlalchemy_inspect",
        broken_inspect,
    )

    with pytest.raises(
        PersonalizationVariableError,
        match="Unsupported personalization value type",
    ):
        pipeline._to_plain_structure(
            FakeORMObject()
        )

def test_resolve_variables_rejects_non_dict_context():
    pipeline = PersonalizationPipeline()

    with pytest.raises(
        PersonalizationVariableError,
        match="Personalization context must be a dictionary",
    ):
        pipeline.resolve_variables("invalid-context")


def test_resolve_variables_rejects_non_dict_resolved_context(
    monkeypatch,
):
    pipeline = PersonalizationPipeline()

    monkeypatch.setattr(
        pipeline,
        "_to_plain_structure",
        lambda value: ["not", "a", "dict"],
    )

    with pytest.raises(
        PersonalizationVariableError,
        match="Resolved personalization context must be a dictionary",
    ):
        pipeline.resolve_variables(
            {"customer_name": "Alice"}
        )


def test_resolve_variables_fills_eta_from_job():
    pipeline = PersonalizationPipeline()

    result = pipeline.resolve_variables(
        {
            "job": {
                "title": "AC Repair",
                "eta": "15 minutes",
            }
        }
    )

    assert result["job"]["eta"] == "15 minutes"
    assert result["eta"] == "15 minutes"

def test_build_declarations_rejects_variable_both_optional_and_required_at_declaration_level(
    monkeypatch,
):
    pipeline = PersonalizationPipeline()

    pipeline.optional_variables = {"customer.name"}
    pipeline.required_variables = {"customer.name"}

    monkeypatch.setattr(
        pipeline.injector,
        "infer_declarations",
        lambda **kwargs: ["customer.name"],
    )

    with pytest.raises(
        PersonalizationVariableError,
        match="Variable cannot be both optional and required",
    ):
        pipeline._build_declarations(
            "Hello {{ customer.name }}"
        )

def test_plain_structure_rejects_excessive_nesting():
    pipeline = PersonalizationPipeline()

    with pytest.raises(
        PersonalizationVariableError,
        match="nesting is too deep",
    ):
        pipeline._to_plain_structure(
            {"value": "test"},
            depth=11,
        )

def test_plain_structure_preserves_datetime_values():
    from datetime import date, datetime, time

    pipeline = PersonalizationPipeline()

    dt = datetime(2026, 8, 17, 14, 30)
    d = date(2026, 8, 17)
    t = time(14, 30)

    assert pipeline._to_plain_structure(dt) is dt
    assert pipeline._to_plain_structure(d) is d
    assert pipeline._to_plain_structure(t) is t

def test_plain_structure_skips_sqlalchemy_column_when_attribute_access_fails(
    monkeypatch,
):
    import app.services.ai.FieldOpsAI.agents.personalization as personalization

    pipeline = PersonalizationPipeline()

    class FakeColumn:
        key = "name"

    class FakeMapper:
        column_attrs = [FakeColumn()]
        relationships = []

    class FakeState:
        mapper = FakeMapper()

    class FakeORMObject:
        @property
        def name(self):
            raise RuntimeError("column access failed")

    monkeypatch.setattr(
        personalization,
        "sqlalchemy_inspect",
        lambda value: FakeState(),
    )

    with pytest.raises(
        PersonalizationVariableError,
        match="Unsupported personalization value type",
    ):
        pipeline._to_plain_structure(
            FakeORMObject()
        )

def test_plain_structure_preserves_datetime_date_and_time_values():
    from datetime import date, datetime, time

    pipeline = PersonalizationPipeline()

    dt = datetime(2026, 8, 17, 14, 30)
    d = date(2026, 8, 17)
    t = time(14, 30)

    assert pipeline._to_plain_structure(dt) == dt
    assert pipeline._to_plain_structure(d) == d
    assert pipeline._to_plain_structure(t) == t

def test_plain_structure_supports_dataclass():
    from dataclasses import dataclass

    @dataclass
    class CustomerData:
        name: str
        city: str

    pipeline = PersonalizationPipeline()

    customer = CustomerData(
        name="Alice",
        city="Chennai",
    )

    result = pipeline._to_plain_structure(customer)

    assert result == {
        "name": "Alice",
        "city": "Chennai",
    }