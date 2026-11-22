from backend.interview_engine.domain.behavioral_blueprint import (
    COMPETENCIES,
    build_behavioral_blueprint,
    seniority_to_difficulty,
)


def test_blueprint_has_five_groups_of_two_slots():
    blueprint = build_behavioral_blueprint("practice", role="Senior Backend Engineer")
    assert [g.competency for g in blueprint.groups] == list(COMPETENCIES)
    assert all(len(g.slots) == 2 for g in blueprint.groups)
    assert len(blueprint.ordered_slots()) == 10


def test_every_slot_is_fully_authored():
    blueprint = build_behavioral_blueprint("practice", role="Mid Engineer")
    for slot in blueprint.ordered_slots():
        assert slot.fallback_question.strip()
        assert slot.follow_up_question.strip()
        assert slot.clarification_text.strip()
        assert slot.hint_text.strip()
        assert slot.target_evidence_count == 1
        assert slot.follow_up_allowance_practice == 1
        assert slot.follow_up_allowance_formal == 0
        assert slot.difficulty == "intermediate"


def test_slot_ids_are_unique_and_competency_scoped():
    blueprint = build_behavioral_blueprint("practice", role="Intern")
    ids = [s.slot_id for s in blueprint.ordered_slots()]
    assert len(ids) == len(set(ids))
    assert ids[0].startswith("problem_solving")


def test_seniority_mapping():
    assert seniority_to_difficulty("Intern", None) == "novice"
    assert seniority_to_difficulty("Junior Developer", None) == "novice"
    assert seniority_to_difficulty("Mid-level Engineer", None) == "intermediate"
    assert seniority_to_difficulty("Senior Engineer", None) == "advanced"
    assert seniority_to_difficulty("Staff Engineer", None) == "advanced"
    assert seniority_to_difficulty("Principal Architect", None) == "advanced"
    assert seniority_to_difficulty("Software Engineer", "no band here") == "intermediate"
    assert seniority_to_difficulty(None, "We need a senior engineer") == "advanced"


def test_formal_blueprint_declares_zero_allowance():
    blueprint = build_behavioral_blueprint("formal", role="Senior Engineer")
    assert all(s.allowance("formal") == 0 for s in blueprint.ordered_slots())
    assert all(s.allowance("practice") == 1 for s in blueprint.ordered_slots())
