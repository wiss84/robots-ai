"""Common constants used across the application."""

# Error messages and fallbacks
EMPTY_RESPONSE_MESSAGE = (
    "I need more context to understand your request. Could you please:\n\n"
    "• Provide more details about what you're trying to do\n"
    "• Break down your request into smaller steps\n"
    "• Share any relevant code or files you're working with\n"
    "• Specify what kind of help you need (e.g., code review, bug fix, feature implementation)"
)

TOOL_ERROR_MESSAGE = (
    "I encountered an issue while trying to help you. To resolve this:\n\n"
    "• Check if the file paths are correct\n"
    "• Ensure you have the necessary permissions\n"
    "• Try breaking down your request into smaller steps\n"
    "• Consider providing more context about what you're trying to achieve"
)

API_QUOTA_ERROR_MESSAGE = (
    "⚠️ **API Quota Exceeded**\n\n"
    "I've reached my current usage limit. Please try again in a few minutes, or consider:\n\n"
    "• Taking a short break between requests\n"
    "• Rephrasing your question more concisely\n"
    "• Using a different agent temporarily\n\n"
    "This is a temporary limitation and should resolve shortly."
)

RATE_LIMIT_ERROR_MESSAGE = (
    "⚠️ **Rate Limit Reached**\n\n"
    "I'm processing too many requests right now. Please wait a moment and try again."
)
