"""search_variables: find catalogue entries from plain words (spec 5, "How the two search tools
match").
"""

import re

from app.catalogue import CatalogueEntry, load_catalogue, to_summary
from app.models import SearchVariablesInput, VariableSummary

# A word is a run of letters or digits, so "root-zone" is two words and "warmer?" is one.
_WORD = re.compile(r"[^\W_]+")

# English words that say nothing about which variable is meant. Without this list, a question
# such as "Is my city getting warmer?" would match every entry through "is" in its definition.
FUNCTION_WORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "so", "than", "then", "as", "if", "not", "no",
        "of", "in", "on", "at", "to", "from", "by", "for", "with", "over", "under", "above",
        "below", "into", "about", "around", "near", "since", "during", "per", "each", "down",
        "is", "are", "was", "were", "be", "been", "being", "am", "do", "does", "did",
        "has", "have", "had", "will", "would", "can", "could", "should", "may", "might",
        "i", "me", "my", "we", "us", "our", "you", "your", "he", "his", "she", "her",
        "it", "its", "they", "them", "their", "this", "that", "these", "those", "there", "here",
        "what", "which", "who", "when", "where", "why", "how",
        "very", "much", "many", "more", "most", "less", "any", "some", "all",
        "get", "gets", "getting", "got", "become", "becomes", "becoming",
    }
)  # fmt: skip


def _words(text: str) -> frozenset[str]:
    return frozenset(_WORD.findall(text.casefold()))


def _query_words(query: str | None) -> frozenset[str]:
    """The query's distinct words, ignoring case, without function words."""
    if query is None:
        return frozenset()
    return _words(query) - FUNCTION_WORDS


def _match_score(query_words: frozenset[str], entry: CatalogueEntry) -> tuple[int, int, int]:
    """How well an entry matches, as counts of query words matched.

    The counts are (anywhere, in keywords, in the name). Tuples compare item by item, so the
    count of matched words decides first, and matches in keywords, then in the name break ties.
    Definition matches count toward the first item only: a narrower entry often repeats a query
    word in its definition, and must not outrank the broader entry the question is about.
    """
    in_keywords = query_words & _words(" ".join(entry.keywords))
    in_name = query_words & _words(entry.name)
    in_definition = query_words & _words(entry.definition)
    matched = in_keywords | in_name | in_definition
    return len(matched), len(in_keywords), len(in_name)


def search_variables(inp: SearchVariablesInput) -> list[VariableSummary]:
    """Catalogue entries that match the query's words, best match first.

    Query words are matched whole and ignoring case against each entry's keywords, name and
    definition, after dropping function words such as "is" and "my". An entry that matches more
    query words comes first; ties go to matches in keywords, then in the name, then to catalogue
    order. `theme`, when given, keeps only entries of exactly that
    theme. An empty query, or one made only of function words, returns every entry of the theme
    in catalogue order. A query that matches nothing returns an empty list.
    """
    entries = [entry for entry in load_catalogue() if inp.theme is None or entry.theme == inp.theme]
    query_words = _query_words(inp.query)
    if not query_words:
        return [to_summary(entry) for entry in entries]
    scored = [(_match_score(query_words, entry), entry) for entry in entries]
    matches = [(score, entry) for score, entry in scored if score[0] > 0]
    # list.sort is stable, also with reverse=True, so equal scores keep catalogue order.
    matches.sort(key=lambda match: match[0], reverse=True)
    return [to_summary(entry) for _, entry in matches]
