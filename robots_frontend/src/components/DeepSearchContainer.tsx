import React, { useState, useEffect, useRef } from 'react';
import './DeepSearchContainer.css';

interface DeepSearchContainerProps {
  messageId?: string; // Unique identifier for this search instance
  isLatestUserMessage?: boolean; // Whether this is the latest user message (should listen to SSE)
  debugInfo?: string; // Debug information to identify which container this is
}

const DeepSearchContainer: React.FC<DeepSearchContainerProps> = ({ messageId, isLatestUserMessage = false, debugInfo }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [urls, setUrls] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [isActive, setIsActive] = useState(false); // Only show when search is active
  const [hasBeenActive, setHasBeenActive] = useState(false); // Track if this container was ever active
  const eventSourceRef = useRef<EventSource | null>(null);
  const currentMessageId = useRef<string | undefined>(messageId);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Reset state when messageId changes (new search)
    if (messageId !== currentMessageId.current) {
      setUrls([]);
      setIsComplete(false);
      setIsActive(false);
      setHasBeenActive(false); // Reset this too when messageId changes
      currentMessageId.current = messageId;
    }

    // If this container is no longer the latest user message, deactivate it
    // This prevents multiple containers from being active simultaneously
    if (!isLatestUserMessage && isActive) {
      console.log(`Deactivating container for messageId: ${messageId} - ${debugInfo}`);
      setIsActive(false);
      return;
    }

    // Only create SSE connection if this is the latest user message
    // This prevents multiple containers from activating simultaneously
    if (!isLatestUserMessage) {
      // For non-latest messages, don't create new connections but keep existing state
      console.log(`Skipping SSE connection for non-latest messageId: ${messageId} - ${debugInfo}`);
      return;
    }

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Abort any existing fetch request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Use fetch with streaming instead of EventSource to avoid CORS issues
    const connectToStream = async () => {
      try {
        // Create new abort controller for this request
        const abortController = new AbortController();
        abortControllerRef.current = abortController;

        console.log(`Starting SSE connection for messageId: ${messageId} (isLatest: ${isLatestUserMessage}) - ${debugInfo}`);
        
        const response = await fetch('http://localhost:8000/sse/urls', {
          method: 'GET',
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
          },
          signal: abortController.signal
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No reader available');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.substring(6);
              if (data.trim() === '') continue;
              
              try {
                const parsedData = JSON.parse(data);

                // Handle search started signal
                if (parsedData?.started) {
                  console.log(`Search started signal received for messageId: ${messageId} - ${debugInfo}`);
                  setIsActive(true);
                  setHasBeenActive(true);
                  continue;
                }

                // Handle completion signal
                if (parsedData?.complete) {
                  console.log(`Search complete signal received for messageId: ${messageId}`);
                  setIsComplete(true);
                  return; // Exit the stream
                }

                // We stream one URL per message
                if (parsedData?.url) {
                  console.log(`URL received for messageId: ${messageId} - ${debugInfo}:`, parsedData.url);
                  // Activate the container when first URL is received if not already active
                  if (!isActive) {
                    console.log(`Activating container on first URL for messageId: ${messageId} - ${debugInfo}`);
                    setIsActive(true);
                    setHasBeenActive(true);
                  }
                  setUrls((prev) => {
                    // Optional: dedupe if you reconnect
                    if (prev.includes(parsedData.url)) return prev;
                    return [...prev, parsedData.url];
                  });
                }
              } catch (error) {
                console.error('Error parsing SSE data:', error);
              }
            }
          }
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          console.log(`SSE connection aborted for messageId: ${messageId}`);
        } else {
          console.error('SSE connection error for messageId:', messageId, error);
        }
      }
    };

    connectToStream();

    // Cleanup function
    return () => {
      // Abort any active fetch request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [messageId, isLatestUserMessage]);

  // Only show the container when search is active OR it has been active before
  // This ensures previous search results remain visible
  if (!isActive && !hasBeenActive) {
    return null;
  }

  // Show the container if we have URLs or if we're in the middle of a search
  // Don't show if it's complete and we have no URLs
  if ((!urls || urls.length === 0) && isComplete) {
    return null;
  }

  // Show placeholder during active search
  if (urls.length === 0 && !isComplete) {
    return (
      <div className="deep-search-container">
        <div className="deep-search-header">
          <span className="deep-search-title">
            🔍 Deep Search
          </span>
          <span className="deep-search-count">
            Searching...
          </span>
          <span className="deep-search-toggle">
            ▶
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="deep-search-container">
      <div
        className="deep-search-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="deep-search-title">
          🔍 Deep Search {isComplete ? '✓' : ''}
        </span>
        <span className="deep-search-count">
          {urls.length} sources
        </span>
        <span className="deep-search-toggle">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {isExpanded && (
        <div className="deep-search-content">
          <div className="deep-search-sources">
            {urls.map((url, index) => (
              <a
                key={index}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="deep-search-link"
              >
                {url}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DeepSearchContainer;