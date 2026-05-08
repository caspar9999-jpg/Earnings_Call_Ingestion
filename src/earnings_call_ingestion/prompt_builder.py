from __future__ import annotations


class PromptBuilder:
    def __init__(self) -> None:
        self._components: list[str] = []

    def add_system_role(self, role: str) -> PromptBuilder:
        self._components.append(role)
        return self

    def add_signal_type_definitions(self, definitions: list[str]) -> PromptBuilder:
        self._components.append("## Signal Type Definitions\n" + "\n".join(f"- {d}" for d in definitions))
        return self

    def add_boundary_rules(self, rules: list[str]) -> PromptBuilder:
        self._components.append("## Boundary Rules\n" + "\n".join(f"- {r}" for r in rules))
        return self

    def add_few_shot_examples(self, examples: list[dict]) -> PromptBuilder:
        import json
        self._components.append(
            "## Few-Shot Examples\n"
            + "\n---\n".join(json.dumps(ex, indent=2) for ex in examples)
        )
        return self

    def add_output_format(self, format: str) -> PromptBuilder:
        self._components.append("## Output Format\n" + format)
        return self

    def build(self) -> str:
        return "\n\n".join(self._components)

    @staticmethod
    def default_pipeline_prompt() -> str:
        return (
            PromptBuilder()
            .add_system_role(
                "You are a supply chain intelligence extraction system. "
                "Extract structured supply chain data from earnings call transcripts."
            )
            .add_signal_type_definitions(
                [
                    "cost_change: direction in (increase, decrease, volatile) — Company's own input/material cost change",
                    "price_adjustment: direction in (increase, decrease, volatile) — Company adjusts prices charged to customers",
                    "market_price_shift: direction in (increase, decrease, volatile) — Benchmark/index market price movement",
                    "production_status_change: direction in (disruption, recovery, increase, decrease, volatile) — Company's own output or production status",
                    "supply_status_change: direction in (disruption, recovery) — External supplier delivery status",
                    "logistics_status_change: direction in (disruption, recovery) — Transportation/logistics channel status",
                    "capacity_expansion: direction in (expansion, contraction) — Production capacity change",
                    "demand_shift: direction in (increase, decrease) — Downstream demand change",
                    "contract_modification: direction in (strengthen, weaken, modify) — Contract terms change",
                    "outlook_uncertainty: direction is always null — Management expresses inability to forecast",
                ]
            )
            .add_boundary_rules(
                [
                    "Structural facts about who supplies whom, who produces what -> Relations",
                    "Explicit relationship establishment or termination -> Relations with valid_from/valid_until",
                    "Physical material-to-product composition (':USED_IN') -> Relations, only when explicitly stated",
                    "State changes: prices, output status, supply status, logistics, demand, capacity -> Signals",
                    "A single source sentence must not appear in both streams; split if necessary",
                    "Entity-anchored uncertainty about future direction -> outlook_uncertainty signal",
                ]
            )
            .add_output_format(
                "Return ONLY valid JSON with two top-level arrays:\n"
                '- "relations": list of relation objects\n'
                '- "signals": list of signal objects\n'
                "Do not include any text outside the JSON object. "
                "Do not auto-assign 'confirmed' as llm_confidence."
            )
            .build()
        )
