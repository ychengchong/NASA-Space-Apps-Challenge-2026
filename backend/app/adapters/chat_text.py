"""Texts of an AI turn that the chat adapter and its OpenAI loop both use (spec 8, "Technical
choices"; spec 10, "Chat request and stream").

They live apart from chat.py so that chat_openai.py, which chat.py imports, can use them too.
"""

# The messages of the `error` event that ends a turn without an answer.
AI_FAILED_MESSAGE = "The AI could not answer just now. The manual controls still work."
AI_REFUSED_MESSAGE = "The AI declined to answer this question. The manual controls still work."
AI_STEP_LIMIT_MESSAGE = "The AI ran out of steps before it finished. Try a simpler question."
AI_CUT_OFF_MESSAGE = "The AI's answer was cut off. Try a simpler question."
AI_TOO_LONG_MESSAGE = "This conversation is too long for the AI. Start a new one."

# A text block that follows earlier text in the turn, such as a note written before a tool call,
# starts a new paragraph, so the screen and the number check see the two apart.
PARAGRAPH_BREAK = "\n\n"
