from typing import List

from pydantic import BaseModel, Field


class BlueprintSlot(BaseModel):
    slot_id: str
    competency: str
    dimension: str
    difficulty: str
    intent: str
    target_evidence_count: int = 1
    follow_up_allowance_practice: int = 1
    follow_up_allowance_formal: int = 0
    fallback_question: str
    follow_up_question: str
    clarification_text: str
    hint_text: str

    def allowance(self, mode: str) -> int:
        return self.follow_up_allowance_formal if mode == "formal" else self.follow_up_allowance_practice


class BlueprintGroup(BaseModel):
    group_id: str
    competency: str
    slots: List[BlueprintSlot]


class Blueprint(BaseModel):
    blueprint_version: str = "behavioral-v1"
    interview_type: str = "behavioral"
    mode: str = "practice"
    weights_version: str = "behavioral-weights-v1"
    adaptation_policy_version: str = "practice-adapt-v1"
    groups: List[BlueprintGroup] = Field(default_factory=list)

    def ordered_slots(self) -> List[BlueprintSlot]:
        return [slot for group in self.groups for slot in group.slots]

    def slot(self, slot_id: str) -> BlueprintSlot:
        for slot in self.ordered_slots():
            if slot.slot_id == slot_id:
                return slot
        raise KeyError(slot_id)
