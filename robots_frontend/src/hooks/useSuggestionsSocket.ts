import { useEffect, useRef, useCallback } from 'react';

export function useSuggestionsSocket(url: string | null, onMessage: (event: MessageEvent) => void) {
  const ws = useRef<WebSocket | null>(null);
  const heartbeatInterval = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const isAlive = useRef(true);
  
  // Configuration - More aggressive to maintain connection
  const HEARTBEAT_INTERVAL = 25000; // 25 seconds - more frequent
  const MAX_RECONNECT_DELAY = 15000; // 15 seconds max - faster reconnection
  const BASE_RECONNECT_DELAY = 500; // 0.5 second base - faster initial reconnection
  const MAX_RECONNECT_ATTEMPTS = 10; // Limit reconnection attempts
  const reconnectAttempts = useRef(0);

  const clearHeartbeat = useCallback(() => {
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
      heartbeatInterval.current = null;
    }
  }, []);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    clearHeartbeat();
    
    heartbeatInterval.current = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        isAlive.current = false; // Will be set to true when we receive pong
        
        try {
          ws.current.send(JSON.stringify({ 
            type: 'ping',
            timestamp: Date.now()
          }));
          
          // If we don't receive a pong within timeout, consider connection dead
          setTimeout(() => {
            if (!isAlive.current && ws.current?.readyState === WebSocket.OPEN) {
              console.log('useSuggestionsSocket: Heartbeat timeout, closing connection');
              try {
                ws.current.close(1002, 'Heartbeat timeout');
              } catch (e) {
                console.warn('useSuggestionsSocket: Error closing connection:', e);
              }
            }
          }, 5000); // 5 second timeout for pong response
        } catch (error) {
          console.error('useSuggestionsSocket: Error sending ping:', error);
          // Connection is probably dead, close it
          if (ws.current) {
            try {
              ws.current.close();
            } catch (e) {
              // Ignore close errors
            }
          }
        }
      }
    }, HEARTBEAT_INTERVAL);
  }, [clearHeartbeat]);

  const connect = useCallback(() => {
    console.log('useSuggestionsSocket: connect called. URL:', url);
    
    if (!url) {
      console.log('useSuggestionsSocket: No URL provided, skipping connection.');
      if (ws.current) {
        ws.current.close(1000, 'URL became null');
        ws.current = null;
      }
      clearHeartbeat();
      clearReconnectTimer();
      return;
    }

    // Don't reconnect if we already have an open connection
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('useSuggestionsSocket: Connection already open.');
      return;
    }

    // Close any existing connection
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

    clearHeartbeat();
    clearReconnectTimer();

    console.log('useSuggestionsSocket: Attempting to connect...');
    
    try {
      const validUrl = new URL(url);
      ws.current = new WebSocket(validUrl.href);

      ws.current.onopen = () => {
        console.log('useSuggestionsSocket: WebSocket connection established');
        reconnectAttempts.current = 0; // Reset reconnect attempts on successful connection
        isAlive.current = true;
        startHeartbeat();
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle server-initiated ping
          if (data.type === 'ping') {
            try {
              if (ws.current?.readyState === WebSocket.OPEN) {
                ws.current.send(JSON.stringify({ 
                  type: 'pong',
                  timestamp: Date.now()
                }));
              }
            } catch (error) {
              console.error('useSuggestionsSocket: Error sending pong:', error);
            }
            return;
          }
          
          // Handle pong response to our ping
          if (data.type === 'pong') {
            isAlive.current = true;
            return;
          }
          
          // Handle deprecated heartbeat_ack for backward compatibility
          if (data.type === 'heartbeat_ack') {
            isAlive.current = true;
            return;
          }
          
        } catch (e) {
          // Ignore parse errors for non-JSON messages
        }
        
        // Forward all other messages to the handler
        onMessage(event);
      };

      ws.current.onerror = (err) => {
        console.error('useSuggestionsSocket: WebSocket error:', err);
      };

      ws.current.onclose = (event) => {
        console.log('useSuggestionsSocket: WebSocket connection closed:', event.code, event.reason);
        ws.current = null;
        clearHeartbeat();

        // Only attempt to reconnect if it wasn't a normal closure and we have a URL
        if (event.code !== 1000 && url && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++;
          const delay = Math.min(
            BASE_RECONNECT_DELAY * Math.pow(1.5, reconnectAttempts.current - 1), // Gentler exponential backoff
            MAX_RECONNECT_DELAY
          );
          
          console.log(`useSuggestionsSocket: Reconnecting in ${delay}ms... (attempt ${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})`);
          
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
          console.warn('useSuggestionsSocket: Max reconnection attempts reached. Stopping reconnection.');
        }
      };

    } catch (error) {
      console.error('useSuggestionsSocket: Invalid WebSocket URL:', url, error);
      return;
    }
  }, [url, onMessage, startHeartbeat, clearHeartbeat, clearReconnectTimer]);

  // Connect and cleanup
  useEffect(() => {
    if (url) {
      console.log('useSuggestionsSocket: useEffect triggered. Calling connect.');
      connect();
    } else {
      // If URL becomes null, close existing connection
      if (ws.current) {
        console.log('useSuggestionsSocket: URL became null, closing connection.');
        ws.current.close(1000, 'URL became null');
        ws.current = null;
      }
      clearHeartbeat();
      clearReconnectTimer();
    }

    return () => {
      console.log('useSuggestionsSocket: Cleanup function called.');
      
      // Clear all timers
      clearHeartbeat();
      clearReconnectTimer();
      
      // Close the socket cleanly only on component unmount
      if (ws.current) {
        const socket = ws.current;
        ws.current = null; // Clear ref before closing to prevent reconnection
        socket.close(1000, 'Component unmounting');
      }
    };
  }, [url, connect, clearHeartbeat, clearReconnectTimer]);

  // Return connection status and manual reconnect function
  return {
    isConnected: ws.current?.readyState === WebSocket.OPEN,
    reconnect: connect,
    disconnect: useCallback(() => {
      if (ws.current) {
        ws.current.close(1000, 'Manual disconnect');
      }
    }, [])
  };
}