"""The provider-output checks of spec 5 and 8, including adversarial strings."""

import hashlib
from typing import Any

import pytest

from app import ai_guard
from app.ai_guard import (
    Evidence,
    GuardReason,
    ProviderDiscovery,
    ProviderExplanation,
    TextRules,
    check_citations,
    check_discovery,
    check_explanation,
    check_place_query,
    check_plain_text,
    check_text,
    mentions_any,
    supported_suggestions,
    text_rules,
    years_in,
)
from app.models import Direction, RetrievedPassage, VerdictKind

INVESTIGATION_ID = "a" * 64
VARIABLE_IDS = frozenset({"air_temp", "precipitation"})
PASSAGE_TEXT = "MERRA-2 starts in 1980. POWER serves T2M on a 0.5 degree grid."


def passage(source_id: str, section_id: str, text: str = PASSAGE_TEXT) -> RetrievedPassage:
    return RetrievedPassage(
        source_id=source_id,
        section_id=section_id,
        text=text,
        file_id="file-1",
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
        score=0.5,
    )


EVIDENCE = Evidence(
    passages=[passage("power", "power-01"), passage("power", "power-02")],
    known_source_ids=frozenset({"power", "project"}),
    known_section_ids=frozenset({"power-01", "power-02", "power-03", "project-01"}),
)


def full_width(text: str) -> str:
    """`text` in full-width forms, which NFKC turns back into ASCII."""
    return "".join(chr(ord(character) + FULL_WIDTH_OFFSET) for character in text)


FULL_WIDTH_OFFSET = 0xFEE0


def rules(*kinds: VerdictKind) -> TextRules:
    return text_rules(range(1981, 2026), [PASSAGE_TEXT], kinds)


def reasons(text: str, text_rules: TextRules) -> list[GuardReason]:
    return [problem.reason for problem in check_text(text, text_rules, "text")]


# Years and identifiers


def test_rules_take_years_and_identifiers_from_the_passages() -> None:
    built = rules()

    assert 1980 in built.allowed_years
    assert 1981 in built.allowed_years and 2025 in built.allowed_years
    assert {"MERRA-2", "T2M"} <= built.allowed_tokens


def test_a_bare_number_in_a_passage_is_not_allowed_in_text() -> None:
    assert "0.5" not in rules().allowed_tokens
    assert reasons("The grid is 0.5 degree.", rules()) == ["number_in_text"]


QUANTITY_PASSAGE = (
    "Values at 2m and 10m differ by 2C. The coefficient is 0.143177157E-1 on a 576-by-361 "
    "grid, with PM2.5 for each 24-hour day."
)


@pytest.mark.parametrize(
    "text",
    [
        "The temperature rose by 2C over the period.",
        "The p-value is 0.143177157E-1.",
        "The record covers 576-by-361 cells.",
        "Wind is measured at 10m.",
        "PM2.5 is reported here.",
    ],
)
def test_a_quantity_mixing_digits_and_letters_in_a_passage_is_not_an_identifier(text: str) -> None:
    quantity_rules = text_rules(range(1981, 2026), [QUANTITY_PASSAGE])

    assert {"2C", "10m", "0.143177157E-1", "576-by-361", "PM2.5"}.isdisjoint(
        quantity_rules.allowed_tokens
    )
    assert "number_in_text" in reasons(text, quantity_rules)


def test_identifiers_starting_with_a_letter_are_taken_from_a_passage() -> None:
    built = text_rules((), ["GEOS-5 and WS10M feed MERRA-2, which serves T2M."])

    assert {"GEOS-5", "WS10M", "MERRA-2", "T2M"} <= built.allowed_tokens


def test_a_trusted_catalogue_phrase_with_a_number_may_be_quoted() -> None:
    catalogue_rules = text_rules(range(1981, 2026), [], allowed_phrases=["Wind speed at 10 m"])

    assert reasons("Wind speed at 10 m tracks the air near the ground.", catalogue_rules) == []
    assert reasons("wind speed at 10 m is the variable here.", catalogue_rules) == []
    assert "number_in_text" in reasons("The wind rose by 10 m per second.", catalogue_rules)


def test_years_in_reads_single_years_and_ranges() -> None:
    assert years_in("From 1990 to 2000, or 1981-2025, not 123 or 12345.") == {
        1990,
        2000,
        1981,
        2025,
    }


@pytest.mark.parametrize(
    "text",
    [
        "The period runs from 1981 to 2025.",
        "The period is 1981-2025.",
        "MERRA-2 begins in 1980.",
        "POWER names this quantity T2M.",
    ],
)
def test_allowed_years_and_identifiers_pass(text: str) -> None:
    assert reasons(text, rules()) == []


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("It rose by 0.3 per decade.", id="decimal"),
        pytest.param("About 12 years had gaps.", id="integer"),
        pytest.param("Warming since 1850.", id="year-outside"),
        pytest.param("The years 1990-2050 matter.", id="range-outside"),
        pytest.param("Roughly 40% of years.", id="percent"),
        pytest.param("Roughly 40 percent.", id="percent-word"),
        pytest.param("It warmed by two degrees.", id="spelled"),
        pytest.param("It warmed by half a degree.", id="half"),
        pytest.param("It is twenty-five millimetres wetter.", id="hyphen-spelled"),
        pytest.param("It warmed \N{FULLWIDTH DIGIT TWO} degrees.", id="full-width"),
        pytest.param("An area of 3 km².", id="superscript"),
        pytest.param("Since the 1990s.", id="decade"),
        pytest.param("The 1st year.", id="ordinal"),
        pytest.param("Use MERRA-3 instead.", id="unknown-identifier"),
        pytest.param("Ⅻ years.", id="roman-numeral"),
        pytest.param("About ½ of the cells.", id="fraction"),
        pytest.param("The rate is 1990 mm per decade.", id="year-with-unit"),
        pytest.param("Roughly 1985 millimetres fell.", id="year-with-unit-word"),
        pytest.param("It was 1990 degrees.", id="year-in-degrees"),
        pytest.param("About 2000 °C.", id="year-with-degree-sign"),
        pytest.param("The rate is 2010 per decade.", id="year-as-rate"),
        pytest.param("The p value is point zero three.", id="spelled-decimal"),
        pytest.param("It warmed by nought point three.", id="nought-point"),
        pytest.param("It rose by twenty five hundredths.", id="number-word-run"),
        pytest.param("It rose by a factor of two.", id="factor"),
        pytest.param("There is a one in twenty chance.", id="odds"),
    ],
)
def test_numbers_other_than_allowed_years_are_rejected(text: str) -> None:
    assert "number_in_text" in reasons(text, rules())


@pytest.mark.parametrize(
    "text",
    [
        "In 1990 the record continues.",
        "The point one should take away is the method.",
        "One place shows a change of source.",
    ],
)
def test_years_and_number_words_that_are_not_quantities_pass(text: str) -> None:
    assert "number_in_text" not in reasons(text, rules())


# Links, markup and hidden characters


@pytest.mark.parametrize(
    "text",
    [
        "Visit https://evil.example/now.",
        "Visit HTTP://EVIL.EXAMPLE.",
        "See www.example.org for more.",
        "See power.larc.nasa.gov for more.",
        "Mail mailto:someone@example.com.",
        "Run javascript:alert(1).",
        "Load data:text/html;base64,AAAA.",
        f"Go to {full_width('https')}://evil.example.",
        "See example.space for more.",
        "Visit nasa dot gov for details.",
    ],
)
def test_urls_are_rejected(text: str) -> None:
    assert "url_in_text" in reasons(text, rules())


@pytest.mark.parametrize(
    "text",
    ["A reanalysis, e.g. MERRA-2, blends a model with observations.", "The cell, i.e. the area."],
)
def test_abbreviations_are_not_urls(text: str) -> None:
    assert "url_in_text" not in reasons(text, rules())


@pytest.mark.parametrize(
    "text",
    [
        "<script>alert(1)</script>",
        "< img src=x>",
        "Close </b> tags.",
        "An &lt;entity&gt; here.",
        "A [link](somewhere).",
        "An ![image](x).",
        "Some `code` here.",
        "Some **bold** text.",
        "# A heading",
    ],
)
def test_markup_is_rejected(text: str) -> None:
    assert "markup_in_text" in reasons(text, rules())


@pytest.mark.parametrize(
    "text",
    [
        "Zero\N{ZERO WIDTH SPACE}width.",
        "Right\N{RIGHT-TO-LEFT OVERRIDE}to-left override.",
        "Byte\u0000order.",
        "Tab\tseparated.",
        "Line\N{LINE SEPARATOR}separator.",
        "Private\ue000use.",
    ],
)
def test_hidden_characters_are_rejected(text: str) -> None:
    assert "hidden_characters" in reasons(text, rules())


def test_a_word_mixing_latin_and_cyrillic_letters_is_rejected() -> None:
    disguised = "The trend is s\N{CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I}gnificant."

    assert "obfuscated_text" in reasons(disguised, rules("not_significant"))


@pytest.mark.parametrize(
    "text",
    ["s-i-g-n-i-f-i-c-a-n-t", "s i g n i f i c a n t", "f.o.r.e.c.a.s.t", "h t t p s evil"],
)
def test_a_word_spread_out_to_hide_it_is_rejected(text: str) -> None:
    assert "obfuscated_text" in reasons(text, rules("not_significant"))


def test_accented_place_names_are_plain_text() -> None:
    assert check_plain_text("São Paulo", "query") == []
    assert check_plain_text("Zürich", "query") == []


def test_plain_text_checks_ignore_numbers() -> None:
    assert check_plain_text("District 9", "query") == []


# The canonical verdict


@pytest.mark.parametrize(
    "text",
    [
        "The trend is significant.",
        "This is a statistically significant warming.",
        "The warming is significantly different from zero.",
        "It shows statistically robust warming.",
        "There is a clear trend here.",
        "This is a real increase.",
        "It is not only significant but large.",
        "There is no doubt it is significant.",
        "The result is not insignificant.",
        "The trend is SIGNIFICANT.",
        f"The trend is {full_width('significant')}.",
        "There is strong evidence of warming here.",
        "The rise is unlikely to be chance.",
        "The rise is not due to chance.",
        "This place has definitely warmed.",
        "The data show a robust and reliable warming trend.",
        "This record shows a meaningful warming trend.",
        "The p-value is small enough to rule out chance.",
        "The p-value is below the usual threshold.",
        "There is no denying the warming is significant.",
        "There is no mistaking a significant trend here.",
        "No wonder the trend is significant.",
        "The warming has never been more significant.",
        "Nothing could be more significant than this trend.",
    ],
)
def test_claiming_significance_contradicts_a_verdict_that_is_not_significant(text: str) -> None:
    assert "contradicts_verdict" in reasons(text, rules("not_significant"))


@pytest.mark.parametrize(
    "text",
    [
        "The trend is not statistically significant.",
        "The result isn't significant.",
        "The result isn\N{RIGHT SINGLE QUOTATION MARK}t significant.",
        "The result is insignificant at this level.",
        "This is a non-significant result.",
        "There is no significant trend here.",
        "The record is too short, so it cannot be called significant.",
        "There is no strong evidence of a trend.",
        "The evidence is too weak to rule out chance.",
        "The evidence cannot rule out chance.",
        "Sen's slope gives a robust trend estimate.",
    ],
)
def test_denying_significance_fits_a_verdict_that_is_not_significant(text: str) -> None:
    assert reasons(text, rules("not_significant")) == []


@pytest.mark.parametrize(
    "text",
    [
        # The closing sentences of the inference_unavailable verdict and of a season's rate.
        "Significance has not been assessed.",
        "Significance was not assessed.",
        "The app reports a rate, but significance is not assessed.",
        "Significance hasn't been assessed.",
    ],
)
@pytest.mark.parametrize("kind", ["inference_unavailable", "too_few_years", "not_significant"])
def test_saying_significance_was_not_assessed_fits_any_verdict_without_inference(
    text: str, kind: VerdictKind
) -> None:
    assert reasons(text, rules(kind)) == []
    assert reasons(text, rules()) == []


@pytest.mark.parametrize(
    "text",
    [
        "The app assesses significance only for eligible annual records.",
        "This seasonal result is descriptive rather than a significance test.",
        "The record is tested for statistical significance with the Mann-Kendall test.",
        "A test of significance needs at least twenty years.",
    ],
)
@pytest.mark.parametrize("kind", ["inference_unavailable", "not_significant", "significant"])
def test_naming_the_significance_test_fits_any_verdict(text: str, kind: VerdictKind) -> None:
    assert reasons(text, rules(kind)) == []
    assert reasons(text, rules()) == []


@pytest.mark.parametrize(
    "text",
    [
        "The test found significance in this record.",
        "The trend tested significant.",
        "The assessment shows the warming is significant.",
        "The trend passes the significance test.",
        "A significance test confirms the warming.",
        "The p-value is below the significance level.",
    ],
)
def test_a_claim_next_to_the_test_still_contradicts_a_verdict_that_is_not_significant(
    text: str,
) -> None:
    assert "contradicts_verdict" in reasons(text, rules("not_significant"))


def test_failing_the_significance_test_contradicts_a_significant_verdict() -> None:
    assert "contradicts_verdict" in reasons(
        "The trend fails the significance test.", rules("significant")
    )


@pytest.mark.parametrize(
    "text",
    ["The trend is not significant.", "This is an insignificant change.", "No significance here."],
)
def test_denying_significance_contradicts_a_significant_verdict(text: str) -> None:
    assert "contradicts_verdict" in reasons(text, rules("significant"))


def test_claiming_significance_fits_a_significant_verdict() -> None:
    assert reasons("The trend is statistically significant.", rules("significant")) == []


@pytest.mark.parametrize(
    "text",
    [
        "Significant means chance alone is unlikely; a result that is not significant would "
        "mean the evidence is too weak.",
        "If the result were not significant, the verdict would say the evidence is too weak.",
    ],
)
def test_describing_the_other_verdict_fits_a_significant_verdict(text: str) -> None:
    assert reasons(text, rules("significant")) == []


def test_a_comparison_may_name_the_significant_place() -> None:
    mixed = rules("significant", "not_significant")

    assert reasons("One place shows a significant trend.", mixed) == []
    assert reasons("The other trend is not significant.", mixed) == []


def test_the_app_name_does_not_turn_a_method_description_into_a_test_outcome() -> None:
    text = (
        "Trend Detective assesses significance only for annual air temperature. "
        "Significance has not been assessed for seasonal rates."
    )

    assert reasons(text, rules("inference_unavailable")) == []


def test_a_significance_detection_is_still_an_outcome() -> None:
    assert "contradicts_verdict" in reasons(
        "The significance test reports a detection.", rules("not_significant")
    )


def test_rather_than_negates_a_formal_significance_finding() -> None:
    assert (
        reasons(
            "The rate is descriptive rather than a formal significance finding.",
            rules("inference_unavailable"),
        )
        == []
    )
    assert "contradicts_verdict" in reasons("The trend is more than significant.", rules())


def test_a_trusted_result_field_name_is_not_a_url() -> None:
    assert (
        reasons("The requested.from and requested.to fields give the years asked for.", rules())
        == []
    )


@pytest.mark.parametrize(
    "text",
    ["https://requested.to", "requested.to/secret", "requested.to?key=x", "requested.to:8000"],
)
def test_a_url_using_a_field_name_is_still_rejected(text: str) -> None:
    assert "url_in_text" in reasons(text, rules())


def test_discovery_text_may_never_claim_significance() -> None:
    assert "contradicts_verdict" in reasons("Rainfall has a significant trend.", rules())


@pytest.mark.parametrize(
    "text",
    [
        "The data show no change.",
        "There is no trend.",
        "There is no real warming here.",
        "The temperature has not changed.",
        "Helsinki has not warmed this century.",
        "The temperature has not changed this decade.",
        "It has not risen any further.",
        "Snow depth has not decreased a lot.",
        "Rainfall did not increase a lot.",
        "Rainfall remained the same.",
        "The values stayed constant.",
        "The series is unchanged.",
    ],
)
def test_asserting_no_change_contradicts_every_verdict(text: str) -> None:
    for kind in ("significant", "not_significant", "too_few_years"):
        assert "contradicts_verdict" in reasons(text, rules(kind))


@pytest.mark.parametrize(
    "text",
    [
        "Not significant does not mean there is no change.",
        "This is not evidence of no trend.",
        "Being not significant, the trend cannot show the series is unchanged.",
    ],
)
def test_negated_no_change_statements_pass(text: str) -> None:
    assert "contradicts_verdict" not in reasons(text, rules("not_significant"))


@pytest.mark.parametrize(
    "text",
    [
        "The test asks how likely data like these would be if there were no trend.",
        "The p-value is computed under the assumption of no trend.",
        "The null hypothesis is that there is no change.",
        "Mann-Kendall checks the data against the idea of no trend.",
        "POWER documents no change of source for haze.",
        "The place name is only a label and does not change the data.",
    ],
)
def test_the_null_hypothesis_and_no_change_of_source_are_not_no_change_claims(text: str) -> None:
    for kind in ("significant", "not_significant", "inference_unavailable"):
        assert reasons(text, rules(kind)) == []


# Directions


def direction_rules(*directions: Direction | None) -> TextRules:
    kinds: tuple[VerdictKind, ...] = tuple(
        "too_few_years" if direction is None else "significant" for direction in directions
    )
    return text_rules(range(1981, 2026), [PASSAGE_TEXT], kinds, directions)


@pytest.mark.parametrize(
    ("text", "directions"),
    [
        pytest.param("The record shows warming.", ("falling",), id="warming-for-falling"),
        pytest.param("The values rose over the period.", ("falling",), id="rose-for-falling"),
        pytest.param("The record shows cooling.", ("rising",), id="cooling-for-rising"),
        pytest.param("Rainfall is declining here.", ("rising", "rising"), id="both-rising"),
        pytest.param("The record shows warming.", (None,), id="untested"),
        pytest.param("Values are falling.", (None, None), id="untested-comparison"),
    ],
)
def test_a_direction_no_place_has_contradicts_the_verdict(
    text: str, directions: tuple[Direction | None, ...]
) -> None:
    assert "contradicts_verdict" in reasons(text, direction_rules(*directions))


@pytest.mark.parametrize(
    ("text", "directions"),
    [
        pytest.param("The record shows warming.", ("rising",), id="matching"),
        pytest.param("One place is warming and one is cooling.", ("rising", "falling"), id="mix"),
        pytest.param("The record is not warming.", ("falling",), id="negated"),
        pytest.param("Sen's slope says how fast values tend to rise.", ("falling",), id="method"),
        pytest.param("The test asks whether it is warming.", (None,), id="whether"),
        pytest.param(
            "With too few years the app cannot say whether it is warming.", (None,), id="cannot"
        ),
    ],
)
def test_a_direction_some_place_has_or_a_framed_one_passes(
    text: str, directions: tuple[Direction | None, ...]
) -> None:
    assert reasons(text, direction_rules(*directions)) == []


def test_discovery_checks_no_direction() -> None:
    assert reasons("Air temperature is the direct measure of warming.", rules()) == []


# Causes and forecasts


@pytest.mark.parametrize(
    "text",
    [
        "The warming is caused by human activity.",
        "The trend is due to emissions.",
        "Greenhouse gases drove the increase.",
        "This rise is because of urbanisation.",
        "The decline results from deforestation.",
        "Climate change explains the warming here.",
        "El Niño affects this record.",
        "The trend can be attributed to land use.",
        "The increase is due to the sensor change.",
        "Rising values are driven by the ocean.",
        "This is the result of global warming.",
        "Humans warmed this place.",
        "Greenhouse gases warmed this place.",
        "Emissions produced this rise.",
        "The rise comes from greenhouse gases.",
        "Warming here reflects human activity.",
        "The warming is a sign of climate change.",
        "The rise is anthropogenic.",
        "Industry made the region warmer.",
        "Burning coal heated the city.",
        "The city was warmed by emissions.",
    ],
)
def test_causal_claims_are_rejected(text: str) -> None:
    assert "causal_claim" in reasons(text, rules("significant"))


@pytest.mark.parametrize(
    "text",
    [
        "This analysis cannot say what caused the warming.",
        "The data do not show whether human activity is responsible.",
        "A trend test does not identify causes.",
        "Sen's slope is used because it resists outliers.",
        "Precipitation is corrected due to gauge undercatch.",
        "The record has a step due to a change of source.",
        "The trend is uncertain because the record is short.",
        "Air temperature is a common way to study climate change.",
        "The app cannot say whether humans caused this.",
    ],
)
def test_method_reasons_and_negated_causes_pass(text: str) -> None:
    assert "causal_claim" not in reasons(text, rules("significant"))


@pytest.mark.parametrize(
    "text",
    [
        "Temperatures will continue to rise.",
        "It will likely keep warming.",
        "Rainfall is projected to fall.",
        "The model predicts more heat.",
        "This forecast shows warming.",
        "In the coming decades it gets hotter.",
        "By the end of the century it doubles.",
        "Extrapolating the line gives a warmer future.",
        "Values are expected to increase.",
        "This trend will persist.",
        "Temperatures are going to rise.",
        "The warming should continue in later decades.",
        "Expect more warming ahead.",
        "It will be hotter soon.",
    ],
)
def test_forecasts_are_rejected(text: str) -> None:
    assert "forecast_claim" in reasons(text, rules("significant"))


@pytest.mark.parametrize(
    "text",
    [
        "This analysis does not forecast future values.",
        "A past trend cannot predict what comes next.",
        "The line is never a projection of the future.",
        "The test cannot predict future values.",
        "You could continue with another place over the same years.",
    ],
)
def test_negated_forecasts_and_advice_pass(text: str) -> None:
    assert "forecast_claim" not in reasons(text, rules("significant"))


@pytest.mark.parametrize(
    "text",
    [
        "MERRA-2 is a reanalysis: it combines observations with a weather model.",
        "A grid cell covers the area around a place, not the exact city.",
        "Sen's slope is the median of the slopes between every pair of years.",
        "The Mann-Kendall test asks whether later years tend to be higher.",
        "You could compare this place with another city over the same years.",
    ],
)
def test_qualitative_explanations_pass(text: str) -> None:
    assert reasons(text, rules("not_significant")) == []


# Citations


def test_a_retrieved_section_or_its_source_is_a_valid_citation() -> None:
    assert check_citations(["power-01"], EVIDENCE, "ids") == []
    assert check_citations(["power"], EVIDENCE, "ids") == []
    assert EVIDENCE.cited("power") == list(EVIDENCE.passages)


@pytest.mark.parametrize(
    ("source_ids", "reason"),
    [
        pytest.param([], "missing_citation", id="none"),
        pytest.param(["made-up"], "unknown_source", id="unknown"),
        pytest.param(["power-03"], "unretrieved_source", id="section-not-retrieved"),
        pytest.param(["project"], "unretrieved_source", id="source-not-retrieved"),
        pytest.param(["https://power.larc.nasa.gov"], "unknown_source", id="url"),
    ],
)
def test_invalid_citations_are_typed(source_ids: list[str], reason: GuardReason) -> None:
    problems = check_citations(source_ids, EVIDENCE, "ids")

    assert [problem.reason for problem in problems] == [reason]


# Whole outputs


def discovery(**changes: Any) -> ProviderDiscovery:
    return ProviderDiscovery.model_validate(
        {
            "status": "ready",
            "suggestions": [
                {
                    "variable_id": "air_temp",
                    "reason": "MERRA-2 describes the air near the ground.",
                    "source_ids": ["power-01"],
                }
            ],
            "place_queries": ["Helsinki"],
            "from": None,
            "to": None,
            "season": None,
            "missing": [],
            "clarification": None,
            **changes,
        }
    )


def explanation(**changes: Any) -> ProviderExplanation:
    return ProviderExplanation.model_validate(
        {
            "status": "answered",
            "investigation_id": INVESTIGATION_ID,
            "blocks": [
                {
                    "text": "MERRA-2 is a reanalysis.",
                    "source_ids": ["power-01"],
                    "references": [{"field": "sen_slope", "place": 0}],
                }
            ],
            "plan": None,
            **changes,
        }
    )


def discovery_reasons(output: ProviderDiscovery) -> list[GuardReason]:
    return [p.reason for p in check_discovery(output, EVIDENCE, rules(), VARIABLE_IDS)]


def explanation_reasons(output: ProviderExplanation, places: int = 1) -> list[GuardReason]:
    problems = check_explanation(
        output, INVESTIGATION_ID, places, EVIDENCE, rules("not_significant"), VARIABLE_IDS
    )
    return [problem.reason for problem in problems]


def test_a_valid_discovery_has_no_problems() -> None:
    assert discovery_reasons(discovery()) == []


def test_a_discovery_suggestion_must_name_a_catalogue_variable() -> None:
    output = discovery(
        suggestions=[{"variable_id": "sea_level", "reason": "Fine.", "source_ids": ["power-01"]}]
    )

    assert discovery_reasons(output) == ["unsupported_variable"]


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        pytest.param({"suggestions": []}, "inconsistent_status", id="ready-empty"),
        pytest.param({"status": "clarify"}, "inconsistent_status", id="clarify-no-question"),
        pytest.param({"status": "unsupported"}, "inconsistent_status", id="unsupported-full"),
    ],
)
def test_a_discovery_status_must_fit_its_content(
    changes: dict[str, Any], reason: GuardReason
) -> None:
    assert discovery_reasons(discovery(**changes)) == [reason]


def test_discovery_checks_every_clarification_text_and_choice() -> None:
    clarification = {
        "question": "Which one, see https://x.example?",
        "choices": [
            {
                "label": "Since 1850",
                "variable_id": "sea_level",
                "place_query": "<b>Paris</b>",
                "from": None,
                "to": None,
                "season": None,
            }
        ],
    }
    output = discovery(status="clarify", suggestions=[], clarification=clarification)

    assert set(discovery_reasons(output)) == {
        "url_in_text",
        "number_in_text",
        "unsupported_variable",
        "markup_in_text",
    }


@pytest.mark.parametrize(
    ("query", "reason"),
    [
        pytest.param(
            "Helsinki, which warmed significantly", "contradicts_verdict", id="significance"
        ),
        pytest.param("Singapore, warmed by emissions", "causal_claim", id="cause"),
        pytest.param("Oslo, which will keep warming", "forecast_claim", id="forecast"),
        pytest.param("Lima at 3 degrees", "number_in_text", id="number"),
        pytest.param(
            "A small fishing town in the far north of the region", "place_query_too_long", id="long"
        ),
    ],
)
def test_a_place_query_that_is_not_a_short_place_name_is_rejected(
    query: str, reason: GuardReason
) -> None:
    assert reason in [problem.reason for problem in check_place_query(query, rules(), "query")]
    assert reason in discovery_reasons(discovery(place_queries=[query]))
    plan = {
        "variable": "air_temp",
        "place_queries": [query],
        "from": None,
        "to": None,
        "season": "annual",
        "ambiguous": False,
    }
    output = explanation(status="new_investigation_required", blocks=[], plan=plan)
    assert reason in explanation_reasons(output)


def test_a_short_place_name_is_a_valid_place_query() -> None:
    assert check_place_query("São Paulo", rules(), "query") == []
    assert check_place_query("St. Petersburg", rules(), "query") == []


def test_a_valid_explanation_has_no_problems() -> None:
    assert explanation_reasons(explanation()) == []


def test_an_explanation_must_be_bound_to_the_requested_investigation() -> None:
    assert explanation_reasons(explanation(investigation_id="b" * 64)) == ["wrong_investigation"]


def test_a_reference_must_name_one_of_the_investigations_places() -> None:
    blocks = [
        {"text": "Fine.", "source_ids": ["power-01"], "references": [{"field": "n", "place": 1}]}
    ]

    assert explanation_reasons(explanation(blocks=blocks)) == ["unknown_reference"]
    assert explanation_reasons(explanation(blocks=blocks), places=2) == []


def test_an_abstention_is_only_checked_for_its_binding() -> None:
    blocks = [{"text": "It rose 9 degrees.", "source_ids": [], "references": []}]

    assert explanation_reasons(explanation(status="insufficient_evidence", blocks=blocks)) == []


@pytest.mark.parametrize(
    ("text", "reference_place"),
    [
        ("Helsinki has a rising trend.", 1),
        ("Helsinki has a significant trend.", 1),
        ("Helsinki has a rising trend.", 0),
        ("The trend is rising.", 1),
        ("The trend is significant.", 1),
    ],
)
def test_comparison_claims_cannot_borrow_another_places_verdict(
    text: str, reference_place: int
) -> None:
    output = explanation(
        blocks=[
            {
                "text": text,
                "source_ids": ["power-01"],
                "references": [{"field": "verdict.sentence", "place": reference_place}],
            }
        ]
    )
    comparison_rules = text_rules(
        (),
        [],
        ("significant", "not_significant"),
        ("rising", "falling"),
        place_labels=("Singapore", "Helsinki"),
    )

    problems = check_explanation(
        output, INVESTIGATION_ID, 2, EVIDENCE, comparison_rules, VARIABLE_IDS
    )

    assert problems


def test_a_comparison_block_can_explain_its_own_places_direction() -> None:
    output = explanation(
        blocks=[
            {
                "text": "Helsinki has a falling trend.",
                "source_ids": ["power-01"],
                "references": [{"field": "verdict.sentence", "place": 1}],
            }
        ]
    )
    comparison_rules = text_rules(
        (),
        [],
        ("significant", "not_significant"),
        ("rising", "falling"),
        place_labels=("Singapore", "Helsinki"),
    )

    assert (
        check_explanation(output, INVESTIGATION_ID, 2, EVIDENCE, comparison_rules, VARIABLE_IDS)
        == []
    )


def test_a_new_investigation_needs_a_plan_with_a_catalogue_variable() -> None:
    plan = {
        "variable": "sea_level",
        "place_queries": ["https://evil.example"],
        "from": None,
        "to": None,
        "season": "annual",
        "ambiguous": False,
    }

    assert explanation_reasons(explanation(status="new_investigation_required", blocks=[])) == [
        "inconsistent_status"
    ]
    assert explanation_reasons(
        explanation(status="new_investigation_required", blocks=[], plan=plan)
    ) == ["unsupported_variable", "url_in_text"]


def test_provider_schemas_are_strict_objects() -> None:
    for model in (ProviderDiscovery, ProviderExplanation):
        schema = model.model_json_schema()
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        for definition in schema["$defs"].values():
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])


def test_provider_output_is_strictly_typed() -> None:
    with pytest.raises(ValueError):
        ai_guard.ProviderDiscovery.model_validate({**discovery().model_dump(), "from": "1990"})


# Citation support of discovery suggestions


TERMS = {"air_temp": ("Air temperature", "T2M", "temperature"), "max_temp": ("T2M_MAX",)}
SUPPORT_EVIDENCE = Evidence(
    passages=[
        passage("power", "power-01", "POWER serves T2M from MERRA-2."),
        passage("power", "power-02", "Precipitation comes from MERRA-2."),
        passage("project", "project-01", "Monthly air  temperature is averaged by day."),
    ],
    known_source_ids=frozenset({"power", "project"}),
    known_section_ids=frozenset({"power-01", "power-02", "project-01"}),
)


def provider_suggestion(variable_id: str, *source_ids: str) -> ai_guard.ProviderSuggestion:
    return ai_guard.ProviderSuggestion(
        variable_id=variable_id, reason="A reason.", source_ids=list(source_ids)
    )


def test_a_citation_whose_passage_never_names_the_variable_is_dropped() -> None:
    (kept,) = supported_suggestions(
        [provider_suggestion("air_temp", "power-02", "power-01")], SUPPORT_EVIDENCE, TERMS
    )

    assert kept.source_ids == ["power-01"]


def test_a_suggestion_left_without_a_citation_is_dropped() -> None:
    suggestions = [
        provider_suggestion("air_temp", "power-02"),
        provider_suggestion("air_temp", "project-01"),
    ]

    kept = supported_suggestions(suggestions, SUPPORT_EVIDENCE, TERMS)

    assert [item.source_ids for item in kept] == [["project-01"]]


def test_a_cited_source_keeps_only_its_sections_naming_the_variable() -> None:
    (kept,) = supported_suggestions(
        [provider_suggestion("air_temp", "power")], SUPPORT_EVIDENCE, TERMS
    )

    assert kept.source_ids == ["power-01"]


def test_a_variable_without_terms_has_no_support() -> None:
    assert (
        supported_suggestions([provider_suggestion("sea_ice", "power-01")], SUPPORT_EVIDENCE, TERMS)
        == []
    )


@pytest.mark.parametrize(
    ("text", "found"),
    [
        pytest.param("POWER serves T2M.", True, id="code"),
        pytest.param("monthly AIR\nTEMPERATURE values", True, id="case-and-whitespace"),
        pytest.param("POWER serves T2M_MAX.", False, id="code-inside-a-longer-code"),
        pytest.param("Temperatures vary.", False, id="part-of-a-word"),
    ],
)
def test_a_term_counts_only_as_a_whole_word(text: str, found: bool) -> None:
    assert mentions_any(text, ("T2M", "air temperature", "temperature")) is found
