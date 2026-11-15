"""The discovery and explanation contracts of spec 5 accept only bounded, typed values."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.catalogue import get_entry, to_summary
from app.models import (
    Citation,
    Clarification,
    DiscoveryRequest,
    DiscoveryResponse,
    DocumentSource,
    ExplanationBlock,
    ExplanationRequest,
    ExplanationResponse,
    ResultReference,
    RetrievedPassage,
    VariableSuggestion,
)

INVESTIGATION_ID = "a" * 64
CITATION: dict[str, Any] = {
    "source_id": "power-methodology",
    "section_id": "power-methodology-01",
    "title": "Methodology",
    "publisher": "NASA POWER",
    "url": "https://power.larc.nasa.gov/docs/methodology/",
    "section": "Meteorology",
    "kind": "agency",
    "passage": "Meteorology parameters come from MERRA-2.",
}
SOURCE: dict[str, Any] = {key: value for key, value in CITATION.items() if key != "passage"} | {
    "accessed": "2026-11-15",
    "sha256": "b" * 64,
}


def test_discovery_request_takes_a_question_and_a_typed_draft() -> None:
    request = DiscoveryRequest.model_validate(
        {
            "question": "Is Singapore getting wetter?",
            "draft": {"variable": "rain", "places": [{"lat": 1.29, "lon": 103.85}], "from": 1990},
        }
    )

    assert request.draft is not None
    assert request.draft.from_ == 1990
    assert request.draft.places[0].lat == 1.29


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"question": ""}, id="empty-question"),
        pytest.param({"question": "x" * 2001}, id="question-too-long"),
        pytest.param({"question": "x", "messages": []}, id="chat-history"),
        pytest.param(
            {"question": "x", "draft": {"places": [{"lat": 0, "lon": 0}] * 5}}, id="five-places"
        ),
        pytest.param({"question": "x", "draft": {"url": "https://example.org"}}, id="draft-url"),
    ],
)
def test_discovery_request_rejects_unbounded_or_unknown_input(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        DiscoveryRequest.model_validate(payload)


@pytest.mark.parametrize(
    "investigation_id",
    ["A" * 64, "a" * 63, "a" * 65, "g" * 64, ""],
)
def test_explanation_request_needs_a_64_lowercase_hex_id(investigation_id: str) -> None:
    with pytest.raises(ValidationError):
        ExplanationRequest(question="Why?", investigation_id=investigation_id)


def test_explanation_request_accepts_a_content_id() -> None:
    assert ExplanationRequest(question="Why?", investigation_id=INVESTIGATION_ID)


@pytest.mark.parametrize(
    "url", ["http://power.larc.nasa.gov/", "javascript:alert(1)", "/docs/method", "https://a b"]
)
def test_citation_links_are_https_only(url: str) -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate({**CITATION, "url": url})


@pytest.mark.parametrize("source_id", ["", "has space", "quote'd", "x" * 121])
def test_citation_rejects_a_source_id_that_is_not_a_slug(source_id: str) -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate({**CITATION, "source_id": source_id})


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"passage": ""}, id="no-passage"),
        pytest.param({"passage": "x" * 1201}, id="passage-too-long"),
        pytest.param({"section_id": "has space"}, id="section-id-not-a-slug"),
        pytest.param({"section_id": None}, id="no-section-id"),
    ],
)
def test_citation_carries_a_bounded_passage_and_a_section_id(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate({**CITATION, **changes})


def test_citation_kind_separates_agency_sources_from_project_notes() -> None:
    assert Citation.model_validate({**CITATION, "kind": "project"}).kind == "project"
    with pytest.raises(ValidationError):
        Citation.model_validate({**CITATION, "kind": "news"})


def test_document_source_keeps_its_access_date_and_content_hash() -> None:
    source = DocumentSource.model_validate(SOURCE)

    assert source.model_dump(mode="json")["accessed"] == "2026-11-15"
    assert source.version is None
    with pytest.raises(ValidationError):
        DocumentSource.model_validate({**source.model_dump(mode="json"), "sha256": "short"})


def test_retrieved_passage_is_capped_and_its_score_is_finite() -> None:
    passage = {
        "source_id": "src",
        "section_id": "src-01",
        "text": "x",
        "file_id": "file-1",
        "content_sha256": "c" * 64,
        "score": 0.5,
    }
    assert RetrievedPassage.model_validate(passage).score == 0.5
    with pytest.raises(ValidationError):
        RetrievedPassage.model_validate({**passage, "text": "x" * 1201})
    with pytest.raises(ValidationError):
        RetrievedPassage.model_validate({**passage, "score": float("nan")})
    with pytest.raises(ValidationError):
        RetrievedPassage.model_validate({**passage, "section_id": "bad section!"})


def test_variable_suggestion_needs_at_least_one_citation() -> None:
    summary = to_summary(get_entry("air_temp"))

    with pytest.raises(ValidationError):
        VariableSuggestion(variable=summary, reason="Relevant.", citations=[])


def test_discovery_response_holds_at_most_three_suggestions() -> None:
    summary = to_summary(get_entry("air_temp"))
    suggestion = VariableSuggestion(
        variable=summary, reason="Relevant.", citations=[Citation.model_validate(CITATION)]
    )
    fields = {"status": "ready", "missing": [], "notices": [], "corpus_version": "v1"}

    assert DiscoveryResponse.model_validate({**fields, "suggestions": [suggestion] * 3})
    with pytest.raises(ValidationError):
        DiscoveryResponse.model_validate({**fields, "suggestions": [suggestion] * 4})


def test_discovery_response_is_labelled_as_written_by_ai() -> None:
    response = DiscoveryResponse(
        status="unsupported",
        reason="unsupported_question",
        suggestions=[],
        missing=["variable"],
        notices=[],
        corpus_version="v1",
    )

    assert response.model_dump()["written_by_ai"] is True


DISCOVERY_FIELDS: dict[str, Any] = {
    "suggestions": [],
    "missing": [],
    "notices": [],
    "corpus_version": "v1",
}


@pytest.mark.parametrize(
    "reason",
    ["no_evidence", "provider_refused", "provider_incomplete", "validation_failed"],
)
def test_unsupported_discovery_names_why_it_found_nothing(reason: str) -> None:
    response = DiscoveryResponse.model_validate(
        {**DISCOVERY_FIELDS, "status": "unsupported", "reason": reason}
    )

    assert response.model_dump(mode="json")["reason"] == reason


def test_unsupported_discovery_without_a_reason_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DiscoveryResponse.model_validate({**DISCOVERY_FIELDS, "status": "unsupported"})


@pytest.mark.parametrize("status", ["ready", "clarify"])
def test_discovery_with_suggestions_or_a_question_has_no_reason(status: str) -> None:
    assert DiscoveryResponse.model_validate({**DISCOVERY_FIELDS, "status": status}).reason is None
    with pytest.raises(ValidationError):
        DiscoveryResponse.model_validate(
            {**DISCOVERY_FIELDS, "status": status, "reason": "no_evidence"}
        )


def test_clarification_offers_at_most_four_choices() -> None:
    choice = {"label": "Annual", "season": "annual"}

    assert Clarification.model_validate({"question": "Which season?", "choices": [choice] * 4})
    with pytest.raises(ValidationError):
        Clarification.model_validate({"question": "Which season?", "choices": [choice] * 5})


def test_clarification_choice_cannot_carry_model_coordinates() -> None:
    with pytest.raises(ValidationError):
        Clarification.model_validate(
            {"question": "Where?", "choices": [{"label": "Here", "lat": 1.0, "lon": 2.0}]}
        )


@pytest.mark.parametrize("field", ["sen_slope", "verdict.kind", "place.name", "requested.from"])
def test_result_reference_accepts_allowlisted_fields(field: str) -> None:
    assert ResultReference.model_validate({"field": field}).place == 0


@pytest.mark.parametrize(
    "reference",
    [
        pytest.param({"field": "ols_p"}, id="field-not-allowlisted"),
        pytest.param({"field": "trend.sen_slope"}, id="unknown-path"),
        pytest.param({"field": "sen_slope", "place": 4}, id="place-out-of-range"),
        pytest.param({"field": "sen_slope", "value": 0.3}, id="model-written-value"),
    ],
)
def test_result_reference_rejects_anything_else(reference: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ResultReference.model_validate(reference)


def test_explanation_block_text_is_bounded() -> None:
    with pytest.raises(ValidationError):
        ExplanationBlock(text="x" * 1201, citations=[], references=[])


def test_explanation_response_binds_one_investigation() -> None:
    response = ExplanationResponse(
        status="answered",
        investigation_id=INVESTIGATION_ID,
        corpus_version="v1",
        blocks=[],
    )

    assert response.model_dump()["written_by_ai"] is True
    assert response.proposal is None
    with pytest.raises(ValidationError):
        ExplanationResponse.model_validate(
            {**response.model_dump(), "investigation_id": "not-an-id"}
        )


EXPLANATION_FIELDS: dict[str, Any] = {
    "investigation_id": INVESTIGATION_ID,
    "corpus_version": "v1",
    "blocks": [],
}


@pytest.mark.parametrize(
    "reason",
    [
        "no_evidence",
        "provider_refused",
        "provider_incomplete",
        "validation_failed",
        "unsupported_question",
    ],
)
def test_insufficient_evidence_names_its_reason(reason: str) -> None:
    response = ExplanationResponse.model_validate(
        {**EXPLANATION_FIELDS, "status": "insufficient_evidence", "reason": reason}
    )

    assert response.model_dump(mode="json")["reason"] == reason


def test_insufficient_evidence_without_a_reason_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ExplanationResponse.model_validate(
            {**EXPLANATION_FIELDS, "status": "insufficient_evidence"}
        )


@pytest.mark.parametrize("status", ["answered", "new_investigation_required"])
def test_an_answer_or_a_new_investigation_has_no_reason(status: str) -> None:
    response = ExplanationResponse.model_validate({**EXPLANATION_FIELDS, "status": status})
    assert response.reason is None
    with pytest.raises(ValidationError):
        ExplanationResponse.model_validate(
            {**EXPLANATION_FIELDS, "status": status, "reason": "no_evidence"}
        )


def test_unknown_reason_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ExplanationResponse.model_validate(
            {**EXPLANATION_FIELDS, "status": "insufficient_evidence", "reason": "timeout"}
        )
