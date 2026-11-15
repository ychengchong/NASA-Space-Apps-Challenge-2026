/**
 * What the "Ask about this investigation" panel says while the server offers no explanations
 * (spec 3, "Ask panel", and spec 8, "When the AI is off"): which AI features are on, and the
 * settings that keep the panel off. The server names each setting by a code, never its value.
 */
import type { AiSetupGap, Capabilities } from "./api";

/** One setting that keeps an AI feature off: the setting to change, and what is wrong with it. */
export interface SetupGapText {
  setting: string;
  problem: string;
}

const GAP_TEXT: Readonly<Record<AiSetupGap, SetupGapText>> = {
  ai_disabled: { setting: "AI_ENABLED", problem: "is not set to true." },
  no_ai_provider: { setting: "AI_PROVIDER", problem: "is not set. This panel needs openai." },
  ai_not_evaluated: { setting: "AI_EVALUATED", problem: "is not set to true." },
  no_ai_model: { setting: "AI_MODEL", problem: "is empty." },
  no_openai_api_key: { setting: "OPENAI_API_KEY", problem: "is empty." },
  no_anthropic_api_key: { setting: "ANTHROPIC_API_KEY", problem: "is empty." },
  no_ollama_digest: { setting: "OLLAMA_MODEL_DIGEST", problem: "is empty." },
  budget_not_durable: { setting: "AI_BUDGET_DURABLE", problem: "is not set to true." },
  no_daily_budget: { setting: "AI_DAILY_BUDGET_MICROUSD", problem: "is not above zero." },
  no_token_prices: {
    setting: "AI_INPUT_MICROUSD_PER_MILLION, AI_OUTPUT_MICROUSD_PER_MILLION",
    problem: "must both be above zero.",
  },
  provider_not_openai: {
    setting: "AI_PROVIDER",
    problem: "names a provider other than openai. This panel needs openai.",
  },
  rag_disabled: { setting: "RAG_ENABLED", problem: "is set to false." },
  no_vector_store: {
    setting: "RAG_VECTOR_STORE_ID",
    problem: "is empty. Upload the corpus and copy the ID the upload prints.",
  },
  malformed_vector_store: {
    setting: "RAG_VECTOR_STORE_ID",
    problem: "is not an OpenAI vector store ID, which starts with vs_.",
  },
  no_corpus_version: {
    setting: "RAG_CORPUS_VERSION",
    problem: "is empty. Copy the version the corpus upload prints.",
  },
  no_corpus_manifest: { setting: "backend/data/corpus/manifest.json", problem: "is missing or unreadable." },
  corpus_version_mismatch: {
    setting: "RAG_CORPUS_VERSION",
    problem:
      "does not match the corpus in this copy of the app. Copy the whole 64-character version the upload prints.",
  },
  no_search_price: { setting: "RAG_SEARCH_MICROUSD_PER_CALL", problem: "is not above zero." },
  discovery_not_evaluated: { setting: "DISCOVERY_EVALUATED", problem: "is set to false." },
  explanations_not_evaluated: { setting: "RAG_EVALUATED", problem: "is set to false." },
};

/** The setting a gap names and what is wrong with it, in plain words. */
export function setupGapText(gap: AiSetupGap): SetupGapText {
  return GAP_TEXT[gap];
}

/** One AI feature and whether the server offers it. */
export interface AiFeatureState {
  label: string;
  on: boolean;
}

/** The three AI features, this panel's first, as the panel lists them. */
export function aiFeatureStates(capabilities: Capabilities): AiFeatureState[] {
  return [
    { label: "Answers in this panel", on: capabilities.ai_explanation_available === true },
    { label: "Suggested variables in the question bar", on: capabilities.ai_discovery_available === true },
    { label: "Case settings proposed from a question", on: capabilities.ai_planner_available },
  ];
}
