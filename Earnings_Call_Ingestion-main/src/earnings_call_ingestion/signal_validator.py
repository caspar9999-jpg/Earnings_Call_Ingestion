from earnings_call_ingestion.schemas import EvidenceQuality, Signal


class SignalValidationResult:
    def __init__(
        self,
        production_signals: list[Signal] | None = None,
        vague_signals: list[Signal] | None = None,
    ) -> None:
        self.production_signals = production_signals or []
        self.vague_signals = vague_signals or []


class SignalValidator:
    def validate(self, signals: list[Signal]) -> SignalValidationResult:
        production: list[Signal] = []
        vague: list[Signal] = []

        for signal in signals:
            if signal.signal_type == "outlook_uncertainty":
                production.append(signal)
            elif signal.evidence_quality in (EvidenceQuality.EXPLICIT, EvidenceQuality.IMPLICIT):
                production.append(signal)
            else:
                vague.append(signal)

        return SignalValidationResult(
            production_signals=production,
            vague_signals=vague,
        )
