"""Source-support evaluation binds judgments to the actual cited request passages."""

import hashlib

import pytest

from scripts.grade_evaluation import Grade, grade_supported, grading_input

TEXT = "A rate alone does not establish a cause."


def case() -> dict:
    return {
        "request": {"question": "Does the rate establish a cause?"},
        "retrievals": [
            {
                "passages": [
                    {
                        "section_id": "methods-01",
                        "text": TEXT,
                        "content_sha256": hashlib.sha256(TEXT.encode()).hexdigest(),
                    }
                ]
            }
        ],
        "response": {
            "investigation_id": "a" * 64,
            "blocks": [
                {
                    "text": "The rate does not establish causation.",
                    "references": [],
                    "citations": [{"section_id": "methods-01"}],
                }
            ],
        },
    }


def test_only_cited_retrieved_evidence_can_support_a_block() -> None:
    payload = grading_input(case(), {})
    assert payload["blocks"][0]["passages"] == {"methods-01": TEXT}
    broken = case()
    broken["response"]["blocks"][0]["citations"] = [{"section_id": "not-retrieved"}]
    with pytest.raises(KeyError):
        grading_input(broken, {})


def test_modified_passage_text_is_rejected_before_a_paid_grade() -> None:
    broken = case()
    broken["retrievals"][0]["passages"][0]["text"] = "A fake claim."
    with pytest.raises(ValueError, match="checksum"):
        grading_input(broken, {})


def test_a_grade_needs_an_actual_support_quote_for_every_block() -> None:
    payload = grading_input(case(), {})
    grade = Grade.model_validate(
        {
            "passed": True,
            "critical_errors": [],
            "blocks": [{"index": 0, "supported": True, "quote": TEXT, "reason": "Direct support."}],
        }
    )
    assert grade_supported(grade, payload)
    grade.blocks[0].quote = "An invented supporting statement."
    assert not grade_supported(grade, payload)
    grade.blocks = []
    assert not grade_supported(grade, payload)


def test_a_critical_error_cannot_be_overridden_by_a_pass_flag() -> None:
    grade = Grade.model_validate(
        {
            "passed": True,
            "critical_errors": ["unsupported_claim"],
            "blocks": [{"index": 0, "supported": True, "quote": TEXT, "reason": "Contradiction."}],
        }
    )
    assert not grade_supported(grade, grading_input(case(), {}))
