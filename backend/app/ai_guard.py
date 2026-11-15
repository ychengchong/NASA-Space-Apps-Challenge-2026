"""Pure checks of provider output for discovery and explanation (spec 5 and spec 8).

The provider's JSON is parsed into the models below, then checked here before anything is shown.
A check returns typed problems; any problem means the output is withheld and the response says
`validation_failed`. These are defensive filters, not proof of truth (spec 8): each block is
checked against its named and referenced places, but evaluation still reviews factual support.

Generated text must stay qualitative. Numbers, dates and units reach the reader through
allowlisted result references that the frontend renders from the trusted Investigation, so
text may hold no digit sequence except a four-digit year the context allows, or an identifier
such as MERRA-2 that the retrieved passages or the catalogue names use verbatim.
"""

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal, get_args

from pydantic import ConfigDict, Field

from app.models import (
    MAX_BLOCKS,
    MAX_CLARIFICATION_CHOICES,
    MAX_COMPARE_PLACES,
    MAX_PASSAGES,
    MAX_REFERENCES,
    MAX_SUGGESTIONS,
    PLACE_NAME_MAX_LENGTH,
    Direction,
    DraftField,
    ExtractedPlan,
    Model,
    ResultField,
    RetrievedPassage,
    Season,
    VerdictKind,
)

GuardReason = Literal[
    "unknown_source",
    "unretrieved_source",
    "missing_citation",
    "wrong_investigation",
    "unknown_reference",
    "unsupported_variable",
    "inconsistent_status",
    "number_in_text",
    "url_in_text",
    "markup_in_text",
    "hidden_characters",
    "obfuscated_text",
    "place_query_too_long",
    "contradicts_verdict",
    "causal_claim",
    "forecast_claim",
]


@dataclass(frozen=True)
class GuardProblem:
    """One reason to withhold the output, and where it was found, such as "blocks[0].text"."""

    reason: GuardReason
    where: str


# Provider output (the strict JSON schemas sent to the provider are built from these)


class _ProviderModel(Model):
    # Strict, as ExtractedPlan is: "1981" is not a year and "false" is not a boolean.
    model_config = ConfigDict(strict=True)


class ProviderSuggestion(_ProviderModel):
    variable_id: str
    reason: str
    source_ids: list[str] = Field(max_length=MAX_PASSAGES)


class ProviderChoice(_ProviderModel):
    """One clarification answer as a typed patch of the draft; the server resolves the place."""

    label: str
    variable_id: str | None
    place_query: str | None
    from_: int | None = Field(alias="from")
    to: int | None
    season: Season | None


class ProviderClarification(_ProviderModel):
    question: str
    choices: list[ProviderChoice] = Field(max_length=MAX_CLARIFICATION_CHOICES)


class ProviderDiscovery(_ProviderModel):
    status: Literal["ready", "clarify", "unsupported"]
    suggestions: list[ProviderSuggestion] = Field(max_length=MAX_SUGGESTIONS)
    place_queries: list[str] = Field(max_length=2)
    from_: int | None = Field(alias="from")
    to: int | None
    season: Season | None
    missing: list[DraftField] = Field(max_length=5)
    clarification: ProviderClarification | None


class ProviderReference(_ProviderModel):
    field: ResultField
    place: int = Field(ge=0, le=MAX_COMPARE_PLACES - 1)


class ProviderBlock(_ProviderModel):
    text: str
    source_ids: list[str] = Field(max_length=MAX_PASSAGES)
    references: list[ProviderReference] = Field(max_length=MAX_REFERENCES)


class ProviderExplanation(_ProviderModel):
    status: Literal["answered", "insufficient_evidence", "new_investigation_required"]
    investigation_id: str
    blocks: list[ProviderBlock] = Field(max_length=MAX_BLOCKS)
    plan: ExtractedPlan | None


# What the checks compare the output against


@dataclass(frozen=True)
class Evidence:
    """The passages retrieved for this request and what the manifest knows."""

    passages: Sequence[RetrievedPassage]
    known_source_ids: frozenset[str]
    known_section_ids: frozenset[str]

    def cited(self, source_id: str) -> list[RetrievedPassage]:
        """The retrieved passages a cited ID names: one section's, or every passage of a
        retrieved source when the model cited the source itself.
        """
        return [
            passage
            for passage in self.passages
            if source_id in (passage.section_id, passage.source_id)
        ]


@dataclass(frozen=True)
class TextRules:
    """What generated text may contain.

    `verdict_kinds` holds the canonical verdict kind of every place of the investigation, or is
    empty when there is no result yet (discovery), so no text may claim significance.
    `directions` holds every place's canonical direction (None for a place without a tested
    direction); it is empty in discovery, where no direction is checked. `allowed_phrases`
    are trusted catalogue texts, such as "Wind speed at 10 m", that text may quote verbatim
    although they hold a number. `place_labels` follows the same order as the verdicts and
    directions, so explanation blocks can be checked against their own places.
    """

    allowed_years: frozenset[int]
    allowed_tokens: frozenset[str]
    verdict_kinds: tuple[VerdictKind, ...] = ()
    directions: tuple[Direction | None, ...] = ()
    allowed_phrases: tuple[str, ...] = ()
    place_labels: tuple[str, ...] = ()


def text_rules(
    allowed_years: Iterable[int],
    trusted_texts: Iterable[str],
    verdict_kinds: Iterable[VerdictKind] = (),
    directions: Iterable[Direction | None] = (),
    allowed_phrases: Iterable[str] = (),
    place_labels: Iterable[str] = (),
) -> TextRules:
    """Rules allowing `allowed_years`, and every four-digit year and every identifier (such as
    MERRA-2 or T2M) that appears verbatim in `trusted_texts`, the retrieved passages. An
    identifier starts with a letter and holds no decimal number, so a quantity such as "2C",
    "10m" or "0.14E-1" in a passage is never allowed: numbers reach the reader through result
    references only. Of `allowed_phrases`, only those holding a digit are kept.
    """
    years = set(allowed_years)
    tokens: set[str] = set()
    for text in trusted_texts:
        years |= years_in(text)
        tokens |= {
            token
            for token in _TOKEN.findall(unicodedata.normalize("NFKC", text))
            if _has_number(token) and _IDENTIFIER.fullmatch(token)
        }
    phrases = tuple(
        unicodedata.normalize("NFKC", phrase) for phrase in allowed_phrases if _has_number(phrase)
    )
    return TextRules(
        frozenset(years),
        frozenset(tokens),
        tuple(verdict_kinds),
        tuple(directions),
        phrases,
        tuple(place_labels),
    )


def years_in(text: str) -> set[int]:
    """The four-digit years written in `text`, alone or in a range such as 1981-2025."""
    return {
        int(part)
        for token in _TOKEN.findall(unicodedata.normalize("NFKC", text))
        for part in _YEAR_SEPARATORS.split(token)
        if _YEAR.fullmatch(part)
    }


# Whole outputs


def check_discovery(
    output: ProviderDiscovery,
    evidence: Evidence,
    rules: TextRules,
    variable_ids: frozenset[str],
) -> list[GuardProblem]:
    """Every problem in a discovery output: each suggestion names a catalogue variable and
    cites a retrieved passage, the status fits the content, and every text is qualitative.
    """
    problems = _discovery_status_problems(output)
    for index, suggestion in enumerate(output.suggestions):
        where = f"suggestions[{index}]"
        if suggestion.variable_id not in variable_ids:
            problems.append(GuardProblem("unsupported_variable", f"{where}.variable_id"))
        problems += check_citations(suggestion.source_ids, evidence, f"{where}.source_ids")
        problems += check_text(suggestion.reason, rules, f"{where}.reason")
    for index, query in enumerate(output.place_queries):
        problems += check_place_query(query, rules, f"place_queries[{index}]")
    if output.clarification is not None:
        problems += check_text(output.clarification.question, rules, "clarification.question")
        for index, choice in enumerate(output.clarification.choices):
            where = f"clarification.choices[{index}]"
            problems += check_text(choice.label, rules, f"{where}.label")
            if choice.variable_id is not None and choice.variable_id not in variable_ids:
                problems.append(GuardProblem("unsupported_variable", f"{where}.variable_id"))
            if choice.place_query is not None:
                problems += check_plain_text(choice.place_query, f"{where}.place_query")
    return problems


def check_explanation(
    output: ProviderExplanation,
    investigation_id: str,
    place_count: int,
    evidence: Evidence,
    rules: TextRules,
    variable_ids: frozenset[str],
    place_labels: frozenset[str] = frozenset(),
) -> list[GuardProblem]:
    """Every problem in an explanation output: it is bound to `investigation_id`, every block
    cites retrieved passages and references a field of one of the `place_count` places, the
    status fits the content, any new plan names a catalogue variable, and every text is
    qualitative and consistent with the canonical verdicts. A plan's place query equal to one
    of `place_labels` (casefolded), the investigation's own labels, is not checked: it stands
    for that place and is never echoed.
    """
    problems: list[GuardProblem] = []
    if output.investigation_id != investigation_id:
        problems.append(GuardProblem("wrong_investigation", "investigation_id"))
    if output.status == "insufficient_evidence":
        # The blocks of an abstention are never shown, so they need no checks.
        return problems
    if output.status == "answered" and not output.blocks:
        problems.append(GuardProblem("inconsistent_status", "blocks"))
    if output.status == "new_investigation_required":
        problems += _plan_problems(output.plan, variable_ids, rules, place_labels)
    for index, block in enumerate(output.blocks):
        where = f"blocks[{index}]"
        problems += check_citations(block.source_ids, evidence, f"{where}.source_ids")
        for ref_index, reference in enumerate(block.references):
            if reference.place >= place_count:
                problems.append(
                    GuardProblem("unknown_reference", f"{where}.references[{ref_index}]")
                )
        for scoped_rules in _block_text_rules(block, rules):
            problems += check_text(block.text, scoped_rules, f"{where}.text")
    return list(dict.fromkeys(problems))


def _block_text_rules(block: ProviderBlock, rules: TextRules) -> list[TextRules]:
    """Check a block against every place it names or references, never another place's result.

    With no explicit place, a comparison claim must hold for all places. A block spanning
    mixed outcomes is withheld; the provider can use separate blocks and canonical verdict
    references instead. Source support and unnamed aliases still need evaluation.
    """
    count = len(rules.place_labels)
    if count < 2 or len(rules.verdict_kinds) != count or len(rules.directions) != count:
        return [rules]
    places = {reference.place for reference in block.references if reference.place < count}
    places.update(
        index
        for index, label in enumerate(rules.place_labels)
        if label.strip() and mentions_any(block.text, (label,))
    )
    return [
        replace(
            rules,
            verdict_kinds=(rules.verdict_kinds[index],),
            directions=(rules.directions[index],),
        )
        for index in sorted(places or set(range(count)))
    ]


def _discovery_status_problems(output: ProviderDiscovery) -> list[GuardProblem]:
    if output.status == "ready" and not output.suggestions:
        return [GuardProblem("inconsistent_status", "suggestions")]
    if output.status == "clarify" and output.clarification is None:
        return [GuardProblem("inconsistent_status", "clarification")]
    if output.status == "unsupported" and (output.suggestions or output.clarification):
        return [GuardProblem("inconsistent_status", "status")]
    return []


def _plan_problems(
    plan: ExtractedPlan | None,
    variable_ids: frozenset[str],
    rules: TextRules,
    place_labels: frozenset[str],
) -> list[GuardProblem]:
    if plan is None:
        return [GuardProblem("inconsistent_status", "plan")]
    problems: list[GuardProblem] = []
    if plan.variable is not None and plan.variable not in variable_ids:
        problems.append(GuardProblem("unsupported_variable", "plan.variable"))
    for index, query in enumerate(plan.place_queries):
        if query.casefold() not in place_labels:
            problems += check_place_query(query, rules, f"plan.place_queries[{index}]")
    return problems


# Citations


def check_citations(
    source_ids: Sequence[str], evidence: Evidence, where: str
) -> list[GuardProblem]:
    """At least one cited ID, each naming a passage retrieved for this request.

    An ID the manifest does not know is `unknown_source`; a known one that this request did not
    retrieve is `unretrieved_source`.
    """
    if not source_ids:
        return [GuardProblem("missing_citation", where)]
    problems: list[GuardProblem] = []
    for index, source_id in enumerate(source_ids):
        if evidence.cited(source_id):
            continue
        known = source_id in evidence.known_section_ids or source_id in evidence.known_source_ids
        reason: GuardReason = "unretrieved_source" if known else "unknown_source"
        problems.append(GuardProblem(reason, f"{where}[{index}]"))
    return problems


def supported_suggestions(
    suggestions: Sequence[ProviderSuggestion],
    evidence: Evidence,
    variable_terms: Mapping[str, Sequence[str]],
) -> list[ProviderSuggestion]:
    """The suggestions with only the citations that mention the suggested variable (spec 8).

    A cited passage supports a suggestion only when it names the variable by one of its
    `variable_terms` (its catalogue name or POWER code) as a whole word, ignoring case. Each
    suggestion keeps the section IDs of its supporting passages, in the order cited, so a
    cited source ID becomes the sections of that source that name the variable. A suggestion
    left with no citation is dropped. The citations must already have passed
    `check_citations`. A mention is necessary, not sufficient: it does not show that
    the passage supports the reason.
    """
    kept: list[ProviderSuggestion] = []
    for suggestion in suggestions:
        terms = variable_terms.get(suggestion.variable_id, ())
        section_ids: list[str] = []
        for source_id in suggestion.source_ids:
            for passage in evidence.cited(source_id):
                if passage.section_id not in section_ids and mentions_any(passage.text, terms):
                    section_ids.append(passage.section_id)
        if section_ids:
            kept.append(suggestion.model_copy(update={"source_ids": section_ids}))
    return kept


def mentions_any(text: str, terms: Iterable[str]) -> bool:
    """Whether `text` holds one of `terms` as a whole word or phrase, ignoring case and
    differences in whitespace. A word joined by "_" is one word, so "T2M" is not found in
    "T2M_MAX".
    """
    normal = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
    return any(
        re.search(rf"(?<!\w){re.escape(' '.join(term.casefold().split()))}(?!\w)", normal)
        for term in terms
        if term.strip()
    )


# Text


# Spec 8: no URLs or markup in generated text; links are the manifest's curated citations. Any
# dotted name ending in two or more letters reads as a domain, except the trusted result-field
# identifiers. Scheme, path, query and port syntax around an identifier still counts as a URL.
_URL = re.compile(
    r"[a-z][a-z0-9+.-]*://|\bwww\.|\b(?:mailto|javascript|vbscript):|\b(?:data|file):\S*/"
    r"|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,24}\b"
    r"|\b\w+\s+dot\s+(?:com|org|net|gov|edu|int|mil|io)\b",
    re.IGNORECASE,
)
_RESULT_FIELD_NAMES = frozenset(get_args(ResultField))
_MARKUP = re.compile(r"<\s*[a-z/!?]|&#?\w+;|\]\(|!\[|`|\*\*|__|^\s*#{1,6}\s", re.I | re.M)
# A word with its joined parts: "MERRA-2", "1981-2025", "0.5", "isn't".
_TOKEN = re.compile(r"\w+(?:[-.,/'\u2019]\w+)*")
# An identifier from a passage: a letter first and no decimal number, as in MERRA-2, T2M,
# WS10M or GEOS-5; "2C", "10m", "0.14E-1", "576-by-361" and "PM2.5" are quantities.
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:-[A-Za-z0-9]+)*")
_YEAR = re.compile(r"[0-9]{4}")
_YEAR_SEPARATORS = re.compile(r"[-/]")
_PERCENT = re.compile(r"[%‰‱]")
# An allowed year written as a quantity: "1990 mm per decade", "2000 °C".
_YEAR_AS_QUANTITY = re.compile(
    r"\b\d{4}\s*(?:°|mm\b|cm\b|m\b|km\b|kg\b|k\b|w\b|kwh\b|mj\b|nm\b|hpa\b|kpa\b|degrees?\b"
    r"|millimet|centimet|kelvin|celsius|fahrenheit|per\b|a\s+year\b|a\s+decade\b|times\b"
    r"|fold\b|units?\b)",
    re.IGNORECASE,
)
_NUMBER_WORDS = (
    r"(?:zero|nought|naught|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    r"|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty"
    r"|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|half|halves|quarter"
    r"|quarters|third|thirds|tenth|tenths|hundredth|hundredths|dozen|double|triple)"
)
_NUMBER_WORD = rf"\b{_NUMBER_WORDS}\b"
_UNIT_WORDS = (
    r"(?:degrees?|°|percent|per\s+cent|percentage\s+points?|millimet(?:re|er)s?|mm|"
    r"centimet(?:re|er)s?|kelvin|celsius|fahrenheit|times|fold|kpa|hpa)"
)
# Spelled quantities: with a unit ("two degrees"), a decimal ("point zero three", but not "the
# point one makes"), a run of number words ("twenty five hundredths"), a factor ("a factor of
# two") or odds ("one in twenty").
_SPELLED_QUANTITY = re.compile(
    rf"\b{_NUMBER_WORDS}(?:[\s-]+(?:a|an|of|and|{_NUMBER_WORDS})){{0,3}}[\s-]+{_UNIT_WORDS}"
    rf"|(?<!\bthe\s)(?<!\ba\s)(?<!\bthis\s)\b(?:point|nought|naught|oh)\s+{_NUMBER_WORD}"
    rf"|{_NUMBER_WORD}(?:[\s-]+(?:and\s+)?{_NUMBER_WORD})+"
    rf"|\bfactor\s+of\s+{_NUMBER_WORD}"
    rf"|{_NUMBER_WORD}\s+in\s+{_NUMBER_WORD}",
    re.IGNORECASE,
)
# The typographic apostrophe (U+2019), read as a plain one.
RIGHT_QUOTE = "\u2019"
_WORD = re.compile(r"[a-z]+(?:['-][a-z]+)*")
_CLAUSE_BREAK = re.compile(
    r"[,.;:!?()\[\]\n]|\b(?:but|although|though|however|while|whereas|yet)\b"
)
_SENTENCE_BREAK = re.compile(r"[.;!?\n]+")
# A negator this many words or fewer before a claim, in the same clause, negates it.
NEGATION_WINDOW = 5
_NEGATORS = frozenset(
    {
        "not", "no", "never", "cannot", "without", "nor", "neither", "unable", "none",
        "lack", "lacks", "lacking", "fail", "fails", "failed", "insufficient", "nothing",
    }
)  # fmt: skip
# "not only significant", "no doubt significant" and "no denying it is significant" affirm
# rather than negate.
_AFFIRMING_AFTER_NEGATOR = frozenset(
    {
        "only", "just", "merely", "doubt", "doubting", "question", "less", "deny", "denying",
        "mistake", "mistaking", "wonder", "disputing", "surprise", "surprising",
    }
)  # fmt: skip
# "never been more significant": a comparative after the negator turns it into an affirmation.
_COMPARATIVES = frozenset({"more", "better", "greater", "bigger", "stronger", "clearer"})

# Spec 7 and 8: only the canonical verdict may call a result significant.
_SIGNIFICANCE = re.compile(
    r"\b(?:insignifican\w*|non-?significan\w*|significan\w*"
    r"|statistically\s+(?:meaningful|robust|reliable|detectable|clear|confirmed)"
    r"|(?:clear|confirmed|proven|definite|real|genuine|undeniable)\s+"
    r"(?:trend|warming|cooling|increase|decrease|rise|decline|change))"
)
_INHERENTLY_NEGATIVE = re.compile(r"^(?:insignifican|non-?significan)")
# "Significance has not been assessed" is the canonical wording of a verdict without inference
# (spec 7): it says what was not done, so it neither claims nor denies significance.
_NOT_ASSESSED = re.compile(
    r"\bsignificance\s+(?:(?:(?:has|have|was|is|were|could|can)(?:\s+not|\s+never|n't)"
    r"|cannot|can't)\s+(?:been\s+|be\s+)?(?:assessed|tested|evaluated|computed|judged"
    r"|determined)|(?:is\s+|was\s+)?unavailable)\b"
)
# Naming the test itself ("a significance test", "the app tests for significance only in
# annual records") describes the method, not this result, so it neither claims nor denies.
_SIGNIFICANCE_METHOD = re.compile(
    r"\bsignificance\s+(?:tests?|testing|levels?|thresholds?|checks?|assessments?)\b"
    r"|\b(?:assess\w*|test\w*|check\w*|evaluat\w*|judg\w*)\s+(?:for\s+)?(?:statistical\s+)?"
    r"significance\b"
    r"|\b(?:a|the)\s+test\s+of\s+(?:statistical\s+)?significance\b"
)
# A sentence that gives the test an outcome ("passes the significance test", "a significance
# test confirms the warming") states a result, so naming the test there is not neutral.
_TEST_OUTCOME = re.compile(
    r"\b(?:pass\w*|fail\w*|meets?|met|clear(?:s|ed|ing)?|reach\w*|surviv\w*|below|under"
    r"|beneath|above|exceed\w*|confirm\w*|show\w*|found|finds?|prov(?:e|es|ed|en|ing)"
    r"|support\w*|detect\w*|indicat\w*|reveal\w*|demonstrat\w*|establish\w*)\b"
)
# Claims of significance in other words, for a verdict that is not significant.
_EVIDENCE_CLAIM = re.compile(
    r"\b(?:strong|clear|convincing|solid|compelling|robust)\s+evidence"
    r"|\b(?:unlikely|not)\s+(?:to\s+be\s+)?(?:due\s+to\s+)?(?:chance|a\s+fluke|random|noise)\b"
    r"|\brul(?:e|es|ed|ing)\s+out\s+chance"
    r"|\b(?:below|under|beneath|passes|meets)\s+the\s+(?:usual\s+)?(?:threshold|cut-?off)"
    r"|\b(?:definitely|certainly|clearly|undoubtedly)\s+(?:warmed|cooled|rose|risen|fell"
    r"|fallen|increased|decreased|changed)"
    r"|\b(?:robust|reliable|meaningful|real)\s+(?:\w+\s+)?trend\b"
    r"(?!\s+(?:estimate|estimator|line|test|method))"
)
# "Too weak to rule out chance" denies the claim without a negator.
_TOO_WEAK_TO = re.compile(r"\btoo\s+\w+\s+to\s*$")
# A denial in a conditional or definitional clause ("if the result were not significant")
# describes the other verdict, not this one.
_CONDITIONAL = re.compile(r"\b(?:if|were|would|a\s+result\s+that|results\s+that)\b")
# Spec 3: "not significant" means insufficient evidence, never "no change". "No change of
# source" describes the data, not the result, and "change" with the data or a result as its
# object ("the label does not change the data") says what something does to the data, not
# how the record behaved. Only those named objects are exempt: "has not changed this decade"
# is still a no-change claim.
_NO_CHANGE = re.compile(
    r"\b(?:no\s+(?:real\s+|actual\s+|clear\s+|meaningful\s+)?"
    r"(?:trend|change(?!\s+(?:of|in\s+(?:source|method|data)))|warming|cooling|increase"
    r"|decrease)\b"
    r"|unchanged\b|(?:has|have|did|does|is|was)\s+not\s+(?:changed?\b"
    r"(?!\s+(?:the|its|their|any)\s+(?:data|values|record|results?|grid\s+cell|series)\b)"
    r"|risen|fallen|increased|decreased|warmed|cooled)\b"
    r"|did\s+not\s+(?:rise|fall|increase|decrease|warm|cool)\b"
    r"|(?:stayed|remained)\s+(?:the\s+same|constant|stable|flat)\b)"
)
# The null hypothesis of the trend test ("the probability if there were no trend") is a
# hypothesis, not a claim about the result.
_HYPOTHESIS = re.compile(
    r"\b(?:if\s+there\s+(?:were|was|is)|assum\w*|hypothes\w*|idea\s+of|under\s+the)\b"
)
# Spec 8: text may not contradict a place's canonical direction.
_RISING = re.compile(
    r"\b(?:ris(?:e|es|ing|en)|rose|increas(?:e|es|ed|ing)|upward|warm(?:ing|ed|er)|wetter"
    r"|hotter)\b"
)
_FALLING = re.compile(
    r"\b(?:fall(?:s|ing|en)?|fell|decreas(?:e|es|ed|ing)|declin(?:e|es|ed|ing)|downward"
    r"|cool(?:ing|ed|er)|drier|drying|colder)\b"
)
# How a method or a hypothetical is described ("how fast values tend to rise", "whether it
# is warming"), which states no direction of this result.
_DIRECTION_FRAME = re.compile(
    r"\b(?:if|whether|would|could|how|tends?\s+to|assum\w*|hypothes\w*)\b"
)
# Spec 8: the AI cannot infer causes. A strong connector makes a causal claim next to a result
# word or a named cause; a weak one, which also explains methods ("used because it is robust"),
# only next to a named cause.
_STRONG_CAUSAL = re.compile(
    r"\b(?:caus(?:e|es|ed|ing)|due\s+to|driven\s+by|drove|drives|because\s+of"
    r"|result(?:s|ed|ing)\s+from|(?:a|the)\s+result\s+of|attribut\w*|responsible\s+for"
    r"|owing\s+to|thanks\s+to|explained\s+by|led\s+to|leads?\s+to|trigger(?:s|ed)?"
    r"|fuel(?:l)?ed\s+by|consequence\s+of|stems?\s+from)\b"
)
_WEAK_CAUSAL = re.compile(
    r"\b(?:because|affect(?:s|ed|ing)?|influenc(?:e|es|ed|ing)|impacts?\s+of|effects?\s+of"
    r"|behind|explains?|driving|contribut\w*)\b"
)
_AGENTS = re.compile(
    r"\b(?:human\s+activit(?:y|ies)|humans|humanity|people|anthropogenic|man-made"
    r"|climate\s+change|global\s+warming|greenhouse|emissions?|carbon\s+dioxide|co2"
    r"|fossil\s+fuels?|coal|industry|industrial|urbani[sz]ation|urban\s+heat|deforestation"
    r"|land[\s-]use|pollution|el\s+ni[nñ]o|la\s+ni[nñ]a|enso)\b"
)
# A named cause as the subject of these verbs makes a causal claim without a connector.
_CAUSE_VERBS = re.compile(
    r"\b(?:produc(?:e|es|ed|ing)|comes?\s+from|came\s+from|reflect(?:s|ed|ing)?|signs?\s+of"
    r"|made)\b"
)
# These adjectives name a cause on their own: "the rise is anthropogenic".
_CAUSAL_ADJECTIVES = re.compile(
    r"\b(?:anthropogenic|man-made|human-made|human-caused|human-induced)\b"
)
# "change" is left out: "a step due to a change of source" explains a caution, not a cause.
_RESULT_WORDS = frozenset(
    {
        "trend", "trends", "warming", "cooling", "rise", "rising", "rose", "risen", "increase",
        "increasing", "increased", "decrease", "decreasing", "decreased", "decline",
        "declining", "declined", "drop", "dropped", "fall", "falling", "fell", "warmed",
        "heated", "cooled", "warmer", "cooler", "wetter", "drier",
    }
)  # fmt: skip
# How near a result word must be to a connector, or after a named cause, to make the sentence
# a causal claim.
RESULT_WORDS_BEFORE = 4
RESULT_WORDS_AFTER = 3
# Spec 1 and 8: the app describes past records and never forecasts. "You could continue" is
# advice to the reader, not a forecast.
_FORECAST = re.compile(
    r"\b(?:forecast\w*|predict\w*|(?:climate|future)\s+projections?|projected\s+to"
    r"|extrapolat\w*|expected\s+to"
    r"|likely\s+to\s+(?:rise|increase|continue|grow|fall|drop|decline|decrease|keep)"
    r"|will\s+(?:likely\s+|probably\s+)?(?:continue|keep|rise|increase|grow|warm|cool|fall"
    r"|drop|decline|decrease|become|reach|exceed|double|get|be\s+(?:warmer|colder|wetter"
    r"|drier|higher|lower))"
    r"|will\s+(?:\w+\s+)?(?:persist|remain|stay|go\s+on|be\s+\w+er)"
    r"|going\s+to\s+(?:rise|increase|continue|keep|grow|fall|drop|decline|warm|cool|get|be)"
    r"|(?<!\byou\s)(?<!\bwe\s)(?:should|may|might|could|would)\s+(?:continue|persist"
    r"|keep\s+\w+ing)"
    r"|expect\s+(?:more|less|further|continued)|ahead|(?:years|decades)\s+to\s+come"
    r"|in\s+the\s+(?:coming|next)\s+\w+|coming\s+(?:years|decades)|next\s+(?:year|decade"
    r"|century)|future\s+(?:values|trends?|temperatures?|rainfall|climate|years)|going\s+forward"
    r"|on\s+track\s+to|set\s+to\s+(?:rise|increase|continue|fall|decline)|by\s+the\s+end\s+of"
    r"\s+the\s+century)\b"
)
# Letters spread out to hide a word ("s-i-g-n-i-f-i-c-a-n-t") are found by these stems once
# every non-letter is removed.
_HIDDEN_STEMS = ("significan", "forecast", "predict", "http", "www")
_MIXED_SCRIPTS = ("LATIN", "CYRILLIC", "GREEK", "ARMENIAN", "CHEROKEE")


def check_text(text: str, rules: TextRules, where: str) -> list[GuardProblem]:
    """Every problem in one generated text: hidden or mixed-script characters, URLs, markup,
    numbers other than allowed years, identifiers and quoted catalogue phrases, claims that
    contradict the canonical verdicts or directions, causal claims and forecasts. Claims are
    read after NFKC normalisation, so full-width letters and ligatures do not slip past.
    """
    problems = check_plain_text(text, where)
    normal = unicodedata.normalize("NFKC", text)
    lower = normal.casefold().replace(RIGHT_QUOTE, "'")
    # Raw text too: NFKC turns a Roman numeral into letters, and the raw form still counts.
    if _has_disallowed_number(text, rules) or _has_disallowed_number(normal, rules):
        problems.append(GuardProblem("number_in_text", where))
    if _hides_a_stem(lower):
        problems.append(GuardProblem("obfuscated_text", where))
    if _contradicts_verdicts(lower, rules.verdict_kinds) or _contradicts_directions(
        lower, rules.directions
    ):
        problems.append(GuardProblem("contradicts_verdict", where))
    if _claims_cause(lower):
        problems.append(GuardProblem("causal_claim", where))
    if _claims_forecast(lower):
        problems.append(GuardProblem("forecast_claim", where))
    return problems


def check_plain_text(text: str, where: str) -> list[GuardProblem]:
    """The checks for text that is never echoed as prose, such as a clarification choice's
    place query: no hidden characters, no words mixing scripts, no URLs and no markup.
    """
    problems: list[GuardProblem] = []
    if any(_is_hidden(character) for character in text):
        problems.append(GuardProblem("hidden_characters", where))
    if any(_mixes_scripts(word) for word in re.findall(r"\w+", text)):
        problems.append(GuardProblem("obfuscated_text", where))
    normal = unicodedata.normalize("NFKC", text)
    if any(
        match.group() not in _RESULT_FIELD_NAMES
        or (match.end() < len(normal) and normal[match.end()] in "/?#:@=&%")
        for match in _URL.finditer(normal)
    ):
        problems.append(GuardProblem("url_in_text", where))
    if _MARKUP.search(normal):
        problems.append(GuardProblem("markup_in_text", where))
    return problems


def check_place_query(query: str, rules: TextRules, where: str) -> list[GuardProblem]:
    """Every problem in a place query the server may echo in a proposal notice ("Choose the
    intended location for '...'"): a place name is short, so a query longer than a place label
    may be is `place_query_too_long`, and it gets every check of `check_text`, so a claim,
    a number or a forecast never reaches the reader through it.
    """
    problems = check_text(query, rules, where)
    if len(query) > PLACE_NAME_MAX_LENGTH:
        problems.append(GuardProblem("place_query_too_long", where))
    return problems


def _is_hidden(character: str) -> bool:
    """Control, format (zero-width, bidirectional), private-use or unassigned characters."""
    if character in "\n ":
        return False
    return unicodedata.category(character) in {"Cc", "Cf", "Co", "Cn", "Cs", "Zl", "Zp"}


def _mixes_scripts(word: str) -> bool:
    scripts = {
        script
        for character in word
        if character.isalpha()
        for script in _MIXED_SCRIPTS
        if unicodedata.name(character, "").startswith(script)
    }
    return len(scripts) > 1


def _has_number(token: str) -> bool:
    return any(unicodedata.numeric(character, None) is not None for character in token)


def _has_disallowed_number(text: str, rules: TextRules) -> bool:
    for phrase in rules.allowed_phrases:
        text = re.sub(re.escape(phrase), " ", text, flags=re.IGNORECASE)
    if _PERCENT.search(text) or _SPELLED_QUANTITY.search(text) or _YEAR_AS_QUANTITY.search(text):
        return True
    return any(
        not _allowed_number_token(token, rules)
        for token in _TOKEN.findall(text)
        if _has_number(token)
    )


def _allowed_number_token(token: str, rules: TextRules) -> bool:
    """A year the rules allow, a range of such years, or a trusted identifier."""
    if token in rules.allowed_tokens:
        return True
    parts = _YEAR_SEPARATORS.split(token)
    return all(_YEAR.fullmatch(part) and int(part) in rules.allowed_years for part in parts)


def _hides_a_stem(lower: str) -> bool:
    letters_only = re.sub(r"[^a-z]", "", lower)
    words_joined = " ".join(_WORD.findall(lower))
    return any(letters_only.count(stem) > words_joined.count(stem) for stem in _HIDDEN_STEMS)


def _contradicts_verdicts(lower: str, kinds: Sequence[VerdictKind]) -> bool:
    """Text claims significance where no place's verdict is significant, or denies it where
    every place's verdict is, or asserts "no change", which no verdict ever means (spec 3).
    Saying that significance was not assessed is neutral, and so are naming the significance
    test in a sentence that gives it no outcome, a denial in a conditional clause and the trend
    test's null hypothesis.
    """
    any_significant = "significant" in kinds
    all_significant = bool(kinds) and all(kind == "significant" for kind in kinds)
    not_assessed = [match.span() for match in _NOT_ASSESSED.finditer(lower)] + [
        match.span()
        for match in _SIGNIFICANCE_METHOD.finditer(lower)
        # The application name is not evidence that a test detected a trend.
        if not _TEST_OUTCOME.search(_sentence(lower, match).replace("trend detective", "the app"))
    ]
    for match in _SIGNIFICANCE.finditer(lower):
        if any(start <= match.start() < end for start, end in not_assessed):
            continue
        inherently_negative = _INHERENTLY_NEGATIVE.match(match.group()) is not None
        affirmed = inherently_negative == _negated(lower, match.start())
        if affirmed and not any_significant:
            return True
        if not affirmed and all_significant and not _CONDITIONAL.search(_clause(lower, match)):
            return True
    if not any_significant and any(
        _claims_evidence(lower, match) for match in _EVIDENCE_CLAIM.finditer(lower)
    ):
        return True
    return any(
        not _negated(lower, match.start()) and not _HYPOTHESIS.search(_clause(lower, match))
        for match in _NO_CHANGE.finditer(lower)
    )


def _claims_evidence(lower: str, match: re.Match[str]) -> bool:
    # "not due to chance" carries its own "not", which affirms; it is not a negator here.
    if match.group().startswith("not"):
        return True
    return not _negated(lower, match.start()) and not _TOO_WEAK_TO.search(_clause(lower, match))


def _contradicts_directions(lower: str, directions: Sequence[Direction | None]) -> bool:
    """Text says the record rises where no place's direction is rising, or falls where none
    is falling; with no tested direction at all, any direction claim contradicts. A negated
    word, or one in a description of the method or a hypothetical, claims nothing. Empty
    `directions` (discovery) check nothing.
    """
    if not directions:
        return False
    for pattern, direction in ((_RISING, "rising"), (_FALLING, "falling")):
        if direction in directions:
            continue
        for match in pattern.finditer(lower):
            framed = _DIRECTION_FRAME.search(_clause(lower, match))
            if not framed and not _negated(lower, match.start()):
                return True
    return False


def _claims_cause(lower: str) -> bool:
    """Whether a sentence ties the result to a cause: a connector that is not negated, a named
    cause followed by a result word, or after one and "by", or with a verb such as "produced",
    or an inherently causal adjective such as "anthropogenic".
    """
    for sentence in _SENTENCE_BREAK.split(lower):
        if any(
            not _negated(sentence, match.start()) for match in _CAUSAL_ADJECTIVES.finditer(sentence)
        ):
            return True
        agents = [
            match for match in _AGENTS.finditer(sentence) if not _negated(sentence, match.start())
        ]
        names_a_cause = bool(agents)
        if names_a_cause and _CAUSE_VERBS.search(sentence):
            return True
        for agent in agents:
            # "Emissions warmed it" and, in the passive, "it was warmed by emissions".
            after = _WORD.findall(sentence[agent.end() :])[:RESULT_WORDS_AFTER]
            before = _WORD.findall(sentence[: agent.start()])[-RESULT_WORDS_BEFORE:]
            if _RESULT_WORDS.intersection(after):
                return True
            if before[-1:] == ["by"] and _RESULT_WORDS.intersection(before):
                return True
        for match in _STRONG_CAUSAL.finditer(sentence):
            if _negated(sentence, match.start()):
                continue
            before = _WORD.findall(sentence[: match.start()])[-RESULT_WORDS_BEFORE:]
            after = _WORD.findall(sentence[match.end() :])[:RESULT_WORDS_AFTER]
            if names_a_cause or _RESULT_WORDS.intersection(before + after):
                return True
        if names_a_cause and any(
            not _negated(sentence, match.start()) for match in _WEAK_CAUSAL.finditer(sentence)
        ):
            return True
    return False


def _claims_forecast(lower: str) -> bool:
    return any(not _negated(lower, match.start()) for match in _FORECAST.finditer(lower))


def _sentence(text: str, match: re.Match[str]) -> str:
    """The whole sentence that holds the match."""
    start = max((brk.end() for brk in _SENTENCE_BREAK.finditer(text, 0, match.start())), default=0)
    following = _SENTENCE_BREAK.search(text, match.end())
    return text[start : following.start() if following else len(text)]


def _clause(text: str, match: re.Match[str]) -> str:
    """The part of the match's clause that comes before it."""
    return _CLAUSE_BREAK.split(text[: match.start()])[-1]


def _negated(text: str, position: int) -> bool:
    """Whether a negator stands up to `NEGATION_WINDOW` words before `position`, in the same
    clause, and is not followed by a word that turns it into an affirmation ("no doubt") or
    by a comparative ("never more significant").
    """
    clause = _CLAUSE_BREAK.split(text[:position])[-1]
    words = _WORD.findall(clause)[-NEGATION_WINDOW:]
    for index, word in enumerate(words):
        if word == "rather" and words[index + 1 : index + 2] == ["than"]:
            return True
        if word not in _NEGATORS and not word.endswith("n't"):
            continue
        following = words[index + 1] if index + 1 < len(words) else ""
        if following in _AFFIRMING_AFTER_NEGATOR:
            continue
        if _COMPARATIVES.intersection(words[index + 1 :]):
            continue
        return True
    return False
