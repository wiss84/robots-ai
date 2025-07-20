/**
 * Frontend conversation summarization utility
 * Calls backend to summarize conversation history
 */

interface ChatMessage {
  role: string;
  content: string;
}

export async function summarizeConversation(messages: ChatMessage[]): Promise<string> {
  if (messages.length === 0) {
    return "No conversation history to summarize.";
  }

  try {
    const response = await fetch('http://localhost:8000/summarize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
      },
      body: JSON.stringify({
        messages: messages
      })
    });

    if (!response.ok) {
      throw new Error(`Summarization failed: ${response.status}`);
    }

    const data = await response.json();
    return data.summary || "Unable to summarize conversation.";

  } catch (error) {
    console.error('Error summarizing conversation:', error);
    return "Error summarizing conversation history.";
  }
}

 