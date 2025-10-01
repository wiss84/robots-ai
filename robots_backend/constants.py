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
    "⚠️ **Service Temporarily Unavailable**\n\n"
    "I'm currently unable to process your request due to one of the following reasons:\n\n"
    "🔹 **All Daily Quotas Exhausted**: You've used all available requests across all models today\n"
    "   → Please try again tomorrow when quotas reset\n\n"
    "🔹 **Temporary API Issues**: Google Gemini API is experiencing temporary issues\n"
    "   → Please wait a few hours and try again\n\n"
    "💡 **Suggestions**:\n"
    "• Try again in a few hours or tomorrow\n"
    "• Check our status page for API updates\n"
    "• Contact support if the issue persists beyond 24 hours\n\n"
    "Thank you for your patience! 🚀"
)

RATE_LIMIT_ERROR_MESSAGE = (
    "⚠️ **Rate Limit Reached**\n\n"
    "I'm processing too many requests right now. Please wait a moment and try again."
)
