from app.services.template_engine import render_template_source


def test_html_template_escapes_xss_payload():
    result = render_template_source(
        body="{{ customer.name }}",
        variables=[{"name": "customer.name", "required": True}],
        context={
            "customer": {
                "name": "<script>alert('XSS')</script>"
            }
        },
        format="html",
    )

    assert "<script>" not in result.body
    assert "&lt;script&gt;" in result.body
def test_html_template_escapes_event_handler_payload():
    result = render_template_source(
        body="{{ customer.name }}",
        variables=[{"name": "customer.name", "required": True}],
        context={
            "customer": {
                "name": '<img src=x onerror="alert(\'XSS\')">'
            }
        },
        format="html",
    )

    assert "<img" not in result.body
    assert "&lt;img" in result.body
def test_html_escapes_javascript_url():
    from app.services.ai.FieldOpsAI.services.prompt_variable_injector import PromptVariableInjector

    injector = PromptVariableInjector()

    result = injector.render(
        body="<a href='{{ url | safe_url }}'>Click here</a>",
        variables=[{"name": "url", "required": True}],
        context={"url": "javascript:alert(1)"},
        html=True,
    )

    assert "javascript:alert(1)" not in result.rendered_body