from typing import Optional, Iterable

__all__ = [
    'IntentMatchResultBase',
    'NluBase'
]


class IntentMatchResultBase:

    def get_confidence(self) -> float:
        raise NotImplementedError

    def get_intent(self) -> str:
        raise NotImplementedError

    def get_slot_value(self, slot_name: str):
        raise NotImplementedError

    def get_all_slots(self) -> dict[str, str]:
        raise NotImplementedError


class NluBase:
    def match_any_intent(self, text: str) -> Optional[IntentMatchResultBase]:
        raise NotImplementedError

    def match_intent_one_of(self, text: str,
                            intents: Iterable[str]) -> Optional[IntentMatchResultBase]:
        raise NotImplementedError
