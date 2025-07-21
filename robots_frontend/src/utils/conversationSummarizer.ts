/**
 * Frontend conversation summarization utility
 * Calls backend to summarize conversation history
 */

interface ChatMessage {
  role: string;
  content: string;
}

export async function summarizeConversationRolling(previousSummary: string, recentMessages: ChatMessage[]): Promise<string> {
  if (recentMessages.length === 0) {
    return previousSummary || "No conversation history to summarize.";
  }

  try {
    const response = await fetch('http://localhost:8000/summarize/rolling', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
      },
      body: JSON.stringify({
        previous_summary: previousSummary,
        new_messages: recentMessages
      })
    });

    if (!response.ok) {
      throw new Error(`Rolling summarization failed: ${response.status}`);
    }

    const data = await response.json();
    return data.summary || "Unable to summarize conversation.";

  } catch (error) {
    console.error('Error rolling summarizing conversation:', error);
    return previousSummary || "Error summarizing conversation history.";
  }
}

 