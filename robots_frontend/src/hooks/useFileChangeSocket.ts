import { useEffect, useState, useRef, useCallback } from 'react';

export function useFileChangeSocket(url: string | null) {
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const heartbeatInterval = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const isAlive = useRef(true);
  
  // Configuration - improved for better stability
  const HEARTBEAT_INTERVAL = 30000; // 30 seconds - more frequent for stability
  const BASE_RECONNECT_DELAY = 1000; // 1 second base - faster reconnection
  const MAX_RECONNECT_DELAY = 30000; // 30 seconds max - faster than before
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
        isAlive.current = false;
        
        try {
          ws.current.send(JSON.stringify({ 
            type: 'ping',
            timestamp: Date.now(),
            source: 'file_watcher'
          }));
          
          // File watcher can be more tolerant of delays
          setTimeout(() => {
            if (!isAlive.current && ws.current?.readyState === WebSocket.OPEN) {
              console.log('useFileChangeSocket: Heartbeat timeout, closing connection');
              try {
                ws.current.close(1002, 'Heartbeat timeout');
              } catch (e) {
                console.warn('useFileChangeSocket: Error closing connection:', e);
              }
            }
          }, 10000); // 10 second timeout (longer than suggestions socket)
        } catch (error) {
          console.error('useFileChangeSocket: Error sending ping:', error);
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
    console.log('useFileChangeSocket: connect called. URL:', url);
    
    if (!url) {
      console.log('useFileChangeSocket: No URL provided, skipping connection.');
      if (ws.current) {
        console.log('useFileChangeSocket: Closing existing connection due to URL becoming null.');
        ws.current.close(1000, 'URL became null');
        ws.current = null;
      }
      setIsConnected(false);
      clearHeartbeat();
      clearReconnectTimer();
      return;
    }

    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('useFileChangeSocket: Connection already open.');
      return;
    }

    // Close any existing connection
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

    clearHeartbeat();
    clearReconnectTimer();
    setIsConnected(false);

    console.log('useFileChangeSocket: Attempting to establish new connection.');
    
    try {
      const validUrl = new URL(url);
      ws.current = new WebSocket(validUrl.href);

      ws.current.onopen = () => {
        console.log('useFileChangeSocket: WebSocket connection established');
        setIsConnected(true);
        reconnectAttempts.current = 0;
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
                  timestamp: Date.now(),
                  source: 'file_watcher'
                }));
              }
            } catch (error) {
              console.error('useFileChangeSocket: Error sending pong:', error);
            }
            return;
          }
          
          // Handle pong response to our ping
          if (data.type === 'pong') {
            isAlive.current = true;
            return;
          }
          
        } catch (e) {
          // Not JSON, treat as file change message
        }
        
        // All file change messages go here
        console.log('useFileChangeSocket: Received file change:', event.data);
        setLastMessage(event.data);
      };

      ws.current.onerror = (err) => {
        console.error('useFileChangeSocket: WebSocket error:', err);
      };

      ws.current.onclose = (event) => {
        console.log('useFileChangeSocket: WebSocket connection closed:', event.code, event.reason);
        ws.current = null;
        setIsConnected(false);
        clearHeartbeat();

        // Reconnect if it wasn't a normal closure and we have a URL
        if (event.code !== 1000 && url && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++;
          const delay = Math.min(
            BASE_RECONNECT_DELAY * Math.pow(1.5, reconnectAttempts.current - 1), // Gentler exponential backoff
            MAX_RECONNECT_DELAY
          );
          
          console.log(`useFileChangeSocket: Reconnecting in ${delay}ms... (attempt ${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})`);
          
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
          console.warn('useFileChangeSocket: Max reconnection attempts reached. Stopping reconnection.');
        }
      };

    } catch (error) {
      console.error('useFileChangeSocket: Invalid WebSocket URL:', url, error);
      return;
    }
  }, [url, startHeartbeat, clearHeartbeat, clearReconnectTimer]);

  // Connect and cleanup
  useEffect(() => {
    if (url) {
      console.log('useFileChangeSocket: useEffect triggered. Calling connect.');
      connect();
    } else {
      // If URL becomes null, close existing connection
      if (ws.current) {
        console.log('useFileChangeSocket: URL became null, closing connection.');
        ws.current.close(1000, 'URL became null');
        ws.current = null;
      }
      setIsConnected(false);
      clearHeartbeat();
      clearReconnectTimer();
    }

    return () => {
      console.log('useFileChangeSocket: Cleanup function called. Closing WebSocket.');
      
      // Clear all timers
      clearHeartbeat();
      clearReconnectTimer();
      
      // Close the socket cleanly only on component unmount
      if (ws.current) {
        const socket = ws.current;
        ws.current = null;
        socket.close(1000, 'Component unmounting');
      }
      
      setIsConnected(false);
    };
  }, [url, connect, clearHeartbeat, clearReconnectTimer]);

  return { 
    lastMessage, 
    isConnected,
    reconnect: connect,
    disconnect: useCallback(() => {
      if (ws.current) {
        ws.current.close(1000, 'Manual disconnect');
      }
    }, [])
  };
}