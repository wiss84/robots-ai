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
  // Only parse messages that start with "I've made the move" to avoid false positives
  if (!responseText.startsWith("I've made the move")) {
    // No chess-related content found
    return {
      isChessResponse: false,
      shouldUpdateBoard: false
    };
  }
  
  // FEN format: pieces turn castling enpassant halfmove fullmove
  // Example: rnbqkb1r/pppppppp/5n2/8/8/4P3/PPPP1PPP/RNBQKBNR w KQkq - 0 2
  // More flexible regex to match FEN pattern
  let fenMatch = responseText.match(/position is ([rnbqkpRNBQKP1-8\/]+ [wb] [KQkq\-]+ [a-h\-1-8]+ \d+ \d+)/);
  
  // Fallback regex for partial matches
  if (!fenMatch) {
    fenMatch = responseText.match(/position is ([rnbqkpRNBQKP1-8\/]+ [wb] [KQkq\-]+ [a-h\-1-8]+ \d+)/);
  }
  
  // Another fallback for even shorter matches
  if (!fenMatch) {
    fenMatch = responseText.match(/position is ([rnbqkpRNBQKP1-8\/]+ [wb] [KQkq\-]+)/);
  }
  
  if (fenMatch) {
    let extractedFen = fenMatch[1].trim();
    
    // Ensure FEN has all 6 components, pad with defaults if missing
    const fenParts = extractedFen.split(' ');
    if (fenParts.length < 6) {
      // Pad with default values
      while (fenParts.length < 6) {
        if (fenParts.length === 1) fenParts.push('w'); // turn
        else if (fenParts.length === 2) fenParts.push('-'); // castling
        else if (fenParts.length === 3) fenParts.push('-'); // enpassant
        else if (fenParts.length === 4) fenParts.push('0'); // halfmove
        else if (fenParts.length === 5) fenParts.push('1'); // fullmove
      }
      extractedFen = fenParts.join(' ');
    }
    
    // Remove the FEN position from the display text
    const displayText = responseText.replace(/The new position is [rnbqkpRNBQKP1-8\/]+ [wb] [KQkq\-]+ [a-h\-1-8]+ \d+ \d+\.?/, '')
                           .replace(/The new position is [rnbqkpRNBQKP1-8\/]+ [wb] [KQkq\-]+ [a-h\-1-8]+ \d+\.?/, '')
                           .replace(/The new position is [rnbqkpRNBQKP1-8\/]+ [wb] [KQkq\-]+\.?/, '')
                           .trim();
    
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