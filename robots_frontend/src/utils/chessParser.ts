// robots_frontend/src/utils/chessParser.ts
export interface ChessParseResult {
  fen?: string;
  isChessResponse: boolean;
  shouldUpdateBoard: boolean;
  displayText?: string; // New field for cleaned display text
}

/**
 * Parse chess-related responses from the games agent
 * @param responseText - The agent's response text
 * @param isGamesAgent - Whether this is the games agent
 * @returns ChessParseResult with parsing information
 */
export function parseChessResponse(responseText: string, isGamesAgent: boolean): ChessParseResult {
  // Only parse chess responses for the games agent
  if (!isGamesAgent) {
    return {
      isChessResponse: false,
      shouldUpdateBoard: false
    };
  }

  // Try to parse as JSON first (fallback for old format)
  let parsed = null;
  let cleanedText = responseText;
  
  if (responseText.startsWith('```json')) {
    cleanedText = responseText.replace(/```json|```/g, '').trim();
  }
  
  try {
    parsed = JSON.parse(cleanedText);
  } catch (e) {
    // Not JSON, continue with natural language parsing
  }

  // If it's valid JSON with FEN, use that
  if (parsed && parsed.fen) {
    return {
      fen: parsed.fen,
      isChessResponse: true,
      shouldUpdateBoard: true,
      displayText: parsed.displayText || parsed.response || responseText
    };
  }

  // Try to extract FEN from natural language and clean the response
  const fenMatch = responseText.match(/position is ([a-zA-Z0-9\/\s\-]+)/);
  if (fenMatch) {
    const extractedFen = fenMatch[1].trim();
    // Remove the FEN position from the display text
    const displayText = responseText.replace(/The new position is [a-zA-Z0-9\/\s\-]+\.?/g, '').trim();
    
    return {
      fen: extractedFen,
      isChessResponse: true,
      shouldUpdateBoard: true,
      displayText: displayText
    };
  }

  // No chess-related content found
  return {
    isChessResponse: false,
    shouldUpdateBoard: false
  };
} 