import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import './AgentSelection.css';
import { agentDescriptions } from '../data/AgentDescriptions';
import Navbar from '../components/Navbar';


export type Agent = {
  id: string;
  name: string;
  description: string;
  avatar: string;
  keywords?: string[];
};

export const agents: Agent[] = [
  {
    id: 'travel',
    name: 'Trip Planner',
    description: agentDescriptions.travel,
    avatar: '/avatars/travel_agent/travel.webp',
    keywords: ['vacation', 'trips', 'travel', 'destinations', 'hotels', 'flights', 'plane', 'car rental', 'travel planning', 'travel tips', 'travel advice', 'trip planning', 'trip advice', 'trip tips', 'travel recommendations', 'trip reommendations']
  },
  {
    id: 'realestate',
    name: 'Home Searcher',
    description: 'Helps with real estate advice and searches.',
    avatar: '/avatars/realestate_agent/realestate.webp',
    keywords: ['houses', 'apartments', 'realestate', 'property', 'flats', 'rent', 'rent flat', 'rent house', 'rent apartment', 'rent property', 'rent flats', 'rent houses', 'buy home', 'buy house', 'buy apartment', 'buy property', 'buy flat']
  },
  {
    id: 'news',
    name: 'News Searcher',
    description: 'Delivers trending news and media.',
    avatar: '/avatars/news_agent/news.webp',
    keywords: ['news', 'headlines', 'media', 'articles', 'current news', 'latest news', 'news articles', 'news headlines', 'news media', 'news articles', 'news headlines']
  },
  {
    id: 'finance',
    name: 'Finance Advisor',
    description: 'Financial insights and tools expert.',
    avatar: '/avatars/finance_agent/finance.webp',
    keywords: ['investments', 'stocks', 'finance', 'loans', 'government bonds', 'investment advice', 'investment tips', 'investment recommendations']
  },
  {
    id: 'image',
    name: 'Image Generator',
    description: 'Generate and display images from text or speech.',
    avatar: '/avatars/image_agent/image_generation.webp',
    keywords: ['image', 'photo', 'image generation', 'Create an image', 'Create a photo', 'Create a picture', 'Create a drawing', 'Create a painting', 'Create a sketch', 'Create a digital art', 'Create a digital painting', 'Create a digital sketch', 'Create a digital drawing','generate an image']
  },
  {
    id: 'coding',
    name: 'Code Advisor',
    description: 'Your expert coding assistant.',
    avatar: '/avatars/coding_agent/coding.webp',
    keywords: ['coding', 'programming', 'developer', 'javascript', 'python', 'code']
  },
  {
    id: 'shopping',
    name: 'Shopping Assistant',
    description: agentDescriptions.shopping,
    avatar: '/avatars/shopping_agent/shopping.webp',
    keywords: ['shopping', 'products', 'deals', 'compare prices']
  },
  {
    id: 'games',
    name: 'Game Buddy',
    description: agentDescriptions.games,
    avatar: '/avatars/games_agent/games.webp',
    keywords: ['chess', 'games','play']
  }
];

function AgentSelection() {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [currentStandingPoseUrl, setCurrentStandingPoseUrl] = useState<string | null>(null);
  const [loadedStandingPoseImages, setLoadedStandingPoseImages] = useState<Set<string>>(new Set());
  const [isCurrentPoseLoading, setIsCurrentPoseLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const navigate = useNavigate();

  // Debounce search query to prevent too many rapid updates
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Optimized search handler
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    try {
      const value = e.target.value;
      console.log('Search input changed:', value);
      setSearchQuery(value);
    } catch (error) {
      console.error('Error updating search query:', error);
    }
  }, []);

  // Global error handler
  useEffect(() => {
    const handleError = (error: ErrorEvent) => {
      console.error('Global error caught:', error);
      setHasError(true);
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error('Unhandled promise rejection:', event.reason);
      setHasError(true);
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, []);

  const filteredAgents = useMemo(() => {
    const query = debouncedSearchQuery.toLowerCase();
    const filtered = agents.filter((agent) =>
      agent.name.toLowerCase().includes(query) ||
      agent.description.toLowerCase().includes(query) ||
      (agent.keywords?.some((kw) => kw.toLowerCase().includes(query)))
    );
    console.log('Search query:', debouncedSearchQuery, 'Filtered agents:', filtered.length);
    return filtered;
  }, [debouncedSearchQuery]);

  // Ensure selectedIndex is always valid when filtered agents change
  useEffect(() => {
    if (filteredAgents.length > 0 && selectedIndex >= filteredAgents.length) {
      setSelectedIndex(0);
    } else if (filteredAgents.length === 0) {
      setSelectedIndex(0);
    }
  }, [filteredAgents, selectedIndex]);

  // Additional safety check for selectedIndex
  const safeSelectedIndex = useMemo(() => {
    if (filteredAgents.length === 0) return 0;
    return Math.max(0, Math.min(selectedIndex, filteredAgents.length - 1));
  }, [selectedIndex, filteredAgents.length]);

  useEffect(() => {
    const preloadImages = async () => {
      try {
        const newLoadedImages = new Set<string>();
        
        // Only preload if we have filtered agents
        if (filteredAgents.length === 0) {
          setLoadedStandingPoseImages(newLoadedImages);
          setCurrentStandingPoseUrl(null);
          setIsCurrentPoseLoading(false);
          return;
        }

        const imagePromises = filteredAgents.map((agent) => {
          const agentFolder = agent.id + '_agent';
          const standingPosePath = `/avatars/${agentFolder}/standing_pose.webp`;
          return new Promise<string>((resolve) => {
            const img = new window.Image();
            img.src = standingPosePath;
            img.onload = () => {
              newLoadedImages.add(standingPosePath);
              resolve(standingPosePath);
            };
            img.onerror = () => {
              // Don't add to loaded images if it fails
              resolve(standingPosePath);
            };
          });
        });

        await Promise.all(imagePromises);
        setLoadedStandingPoseImages(newLoadedImages);
        
        // Ensure selectedIndex is within bounds
        const safeSelectedIndex = Math.min(selectedIndex, filteredAgents.length - 1);
        if (safeSelectedIndex !== selectedIndex) {
          setSelectedIndex(safeSelectedIndex);
        }
        
        // Update current standing pose after preloading
        if (filteredAgents.length > 0 && safeSelectedIndex >= 0) {
          const agentFolder = filteredAgents[safeSelectedIndex].id + '_agent';
          const standingPosePath = `/avatars/${agentFolder}/standing_pose.webp`;
          setCurrentStandingPoseUrl(standingPosePath);
          setIsCurrentPoseLoading(!newLoadedImages.has(standingPosePath));
        } else {
          setCurrentStandingPoseUrl(null);
          setIsCurrentPoseLoading(false);
        }
      } catch (error) {
        console.error('Error preloading images:', error);
        // Fallback: set loading to false to prevent infinite loading state
        setIsCurrentPoseLoading(false);
        setCurrentStandingPoseUrl(null);
      }
    };

    preloadImages();
  }, [filteredAgents]); // Remove selectedIndex from dependencies to prevent infinite loops

  // Separate useEffect to handle selectedIndex changes
  useEffect(() => {
    if (filteredAgents.length > 0 && safeSelectedIndex >= 0 && safeSelectedIndex < filteredAgents.length) {
      const agentFolder = filteredAgents[safeSelectedIndex].id + '_agent';
      const standingPosePath = `/avatars/${agentFolder}/standing_pose.webp`;
      setCurrentStandingPoseUrl(standingPosePath);
      setIsCurrentPoseLoading(!loadedStandingPoseImages.has(standingPosePath));
    }
  }, [safeSelectedIndex, filteredAgents, loadedStandingPoseImages]);

  const rotateLeft = () => {
    setSelectedIndex((prev) => (prev - 1 + filteredAgents.length) % filteredAgents.length);
  };

  const rotateRight = () => {
    setSelectedIndex((prev) => (prev + 1) % filteredAgents.length);
  };

  const rotation = filteredAgents.length > 0
    ? 270 - (safeSelectedIndex * (360 / filteredAgents.length))
    : 0;

  // Search box to be rendered in Navbar
  const searchBox = (
    <input
      type="text"
      className="agent-search-box"
      placeholder="Search agents..."
      value={searchQuery}
      onChange={handleSearchChange}
    />
  );

  return (
    <>
      <Navbar showHomeLink={true} showAgentSelectionLink={false} searchBox={searchBox} />
      <div className="app">
        <h1>Select Your Agent</h1>
        {hasError ? (
          <div className="agent-selection-error-container">
            <h2>Something went wrong</h2>
            <p>Please refresh the page and try again.</p>
            <button 
              onClick={() => {
                setHasError(false);
                setSearchQuery('');
                setSelectedIndex(0);
              }}
              className="agent-selection-error-button"
            >
              Reset
            </button>
          </div>
        ) : (
          <div className="main-content">
            <div className="avatar-circle">
              {/* Display loading indicator or standing pose image */}
              {isCurrentPoseLoading && currentStandingPoseUrl && !loadedStandingPoseImages.has(currentStandingPoseUrl) ? (
                <div className="loading-indicator">Loading Agent...</div>
              ) : (
                currentStandingPoseUrl && (
                  <img
                    src={currentStandingPoseUrl}
                    alt="Selected Agent Standing Pose"
                    className="standing-pose-image"
                    onError={(e) => {
                      e.currentTarget.src = 'https://placehold.co/200x300/CCCCCC/000000?text=Image+Not+Found';
                      e.currentTarget.alt = 'Image not found';
                      setIsCurrentPoseLoading(false);
                    }}
                    onLoad={() => setIsCurrentPoseLoading(false)}
                  />
                )
              )}

              {/* Render mini avatars around the circle */}
              {filteredAgents.length > 0 ? (
                filteredAgents.map((agent, index) => {
                  try {
                    const angle = (360 / filteredAgents.length) * index + rotation;
                    const x = 350 * Math.cos((angle * Math.PI) / 180);
                    const y = 350 * Math.sin((angle * Math.PI) / 180);
                    
                    return (
                      <div
                        key={agent.id}
                        className={`avatar-wrapper ${safeSelectedIndex === index ? 'active-avatar' : ''}`}
                        style={{ transform: `translate(${x}px, ${y}px)` }}
                        onClick={() => setSelectedIndex(index)}
                      >
                        <img 
                          src={agent.avatar} 
                          alt={agent.name} 
                          className="avatar"
                          onError={(e) => {
                            e.currentTarget.src = 'https://placehold.co/70x70/CCCCCC/000000?text=Agent';
                            e.currentTarget.alt = 'Agent placeholder';
                          }}
                        />
                        <span>{agent.name}</span>
                      </div>
                    );
                  } catch (error) {
                    console.error('Error rendering avatar:', error);
                    setHasError(true);
                    return null;
                  }
                })
              ) : (
                <div className="no-agents-found-message">
                  <h3>No agents found</h3>
                  <p>Try a different search term</p>
                </div>
              )}
            </div>

            {filteredAgents.length > 0 && (
              <div className="preview-card">
                <h2 className="preview-name">{filteredAgents[safeSelectedIndex].name}</h2>
                <img
                  src={filteredAgents[safeSelectedIndex].avatar}
                  alt={filteredAgents[safeSelectedIndex].name}
                  className="preview-avatar"
                  onError={(e) => {
                    e.currentTarget.src = 'https://placehold.co/150x150/CCCCCC/000000?text=Agent';
                    e.currentTarget.alt = 'Agent placeholder';
                  }}
                />
                <p>Click "Details" to view this agent's full description and capabilities.</p>
                <button onClick={() => navigate('/details', { state: { agent: filteredAgents[safeSelectedIndex] } })}>
                  Details
                </button>
              </div>
            )}
          </div>
        )}

        {filteredAgents.length > 0 && !hasError && (
          <div className="arrow-controls">
            <div className="arrow-group">
              <span className="arrow-label">Cycle Left</span>
              <button className="arrow-button left" onClick={rotateLeft}>
                <img src="/assets/left.webp" alt="Left Arrow" className="arrow-icon" />
              </button>
            </div>
            <div className="arrow-group">
              <span className="arrow-label">Cycle Right</span>
              <button className="arrow-button right" onClick={rotateRight}>
                <img src="/assets/right.webp" alt="Right Arrow" className="arrow-icon" />
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default AgentSelection;