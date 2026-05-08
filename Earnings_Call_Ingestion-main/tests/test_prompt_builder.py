from earnings_call_ingestion.prompt_builder import PromptBuilder


class TestPromptBuilder:
    def test_builds_prompt_with_all_components(self):
        builder = PromptBuilder()
        prompt = (
            builder.add_system_role("You extract supply chain data from earnings calls.")
            .add_signal_type_definitions(
                [
                    "cost_change: direction in (increase, decrease, volatile)",
                    "demand_shift: direction in (increase, decrease)",
                ]
            )
            .add_boundary_rules(
                [
                    "Structural facts about who supplies whom -> Relations",
                    "State changes (prices, output) -> Signals",
                ]
            )
            .add_few_shot_examples(
                [
                    {"transcript": "Costs rose 10%", "expected": "cost_change"},
                ]
            )
            .add_output_format("Return JSON with 'relations' and 'signals' arrays.")
            .build()
        )
        assert "You extract supply chain data" in prompt
        assert "cost_change" in prompt
        assert "Structural facts" in prompt
        assert "Costs rose 10%" in prompt
        assert "relations" in prompt

    def test_builds_minimal_prompt(self):
        builder = PromptBuilder()
        prompt = builder.add_system_role("Test role.").add_output_format("JSON.").build()
        assert "Test role." in prompt
        assert "JSON." in prompt

    def test_components_appear_in_order_added(self):
        builder = PromptBuilder()
        prompt = (
            builder.add_system_role("ROLE")
            .add_signal_type_definitions(["SIGNAL_DEFS"])
            .add_boundary_rules(["BOUNDARY"])
            .add_few_shot_examples([{"text": "FEW_SHOT"}])
            .add_output_format("FORMAT")
            .build()
        )
        role_pos = prompt.index("ROLE")
        signal_pos = prompt.index("SIGNAL_DEFS")
        boundary_pos = prompt.index("BOUNDARY")
        few_shot_pos = prompt.index("FEW_SHOT")
        format_pos = prompt.index("FORMAT")
        assert role_pos < signal_pos < boundary_pos < few_shot_pos < format_pos

    def test_default_pipeline_prompt_includes_all_signal_types(self):
        prompt = PromptBuilder.default_pipeline_prompt()
        types = [
            "cost_change",
            "price_adjustment",
            "market_price_shift",
            "production_status_change",
            "supply_status_change",
            "logistics_status_change",
            "capacity_expansion",
            "demand_shift",
            "contract_modification",
            "outlook_uncertainty",
        ]
        for t in types:
            assert t in prompt, f"Missing signal type: {t}"

    def test_default_pipeline_prompt_includes_boundary_rules(self):
        prompt = PromptBuilder.default_pipeline_prompt()
        assert "Relations" in prompt
        assert "Signals" in prompt
        assert "boundary" in prompt.lower()
