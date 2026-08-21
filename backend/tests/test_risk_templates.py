from app.models.risk_template import RiskTemplate


def test_create_risk_template_model():
    rt = RiskTemplate(
        id="test-id-1",
        user_id="user_1",
        name="Conservative Kelly",
        description="Half-kelly with 15% drawdown limit",
        rules=[
            {
                "condition": {"type": "max_drawdown", "params": {"threshold": 0.15}},
                "action": {"type": "reject", "params": {}},
            },
            {
                "condition": {"type": "min_confidence", "params": {"min_confidence": 0.5}},
                "action": {"type": "approve", "params": {}},
            },
        ],
    )
    assert rt.user_id == "user_1"
    assert rt.name == "Conservative Kelly"
    assert len(rt.rules) == 2
    assert rt.id == "test-id-1"
