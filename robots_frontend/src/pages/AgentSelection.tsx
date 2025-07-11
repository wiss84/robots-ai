import { useState, useEffect, useMemo } from 'react';
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

const agents: Agent[] = [
  {
    id: 'travel',
    name: 'Trip Planner',
    description: agentDescriptions.travel,
    avatar: '/avatars/travel_agent/travel.webp',
    keywords: ['vacation', 'trips', 'travel', 'destinations', 'hotels', 'flights', 'plane', 'car rental']
  },
  {
    id: 'realestate',
    name: 'Home Searcher',
    description: 'Helps with real estate advice and searches.',
    avatar: '/avatars/realestate_agent/realestate.webp',
    keywords: ['houses', 'apartments', 'property', 'flats', 'rent', 'buy home']
  },
  {
    id: 'news',
    name: 'News Searcher',
    description: 'Delivers trending news and media.',
    avatar: '/avatars/news_agent/news.webp',
    keywords: ['news', 'headlines', 'media', 'articles']
  },
  {
    id: 'finance',
    name: 'Finance Advisor',
    description: 'Financial insights and tools expert.',
    avatar: '/avatars/finance_agent/finance.webp',
    keywords: ['money', 'investments', 'budget', 'stocks', 'finance', 'loans']
  },
  {
    id: 'image',
    name: 'Image Generator',
    description: 'Generate and display images from text or speech.',
    avatar: '/avatars/image_agent/image_generation.webp',
    keywords: ['image', 'photo', 'generation']
  },
  {
    id: 'coding',
    name: 'Code Advisor',
    description: 'Your expert coding assistant.',
    avatar: '/avatars/coding_agent/coding.webp',
    keywords: ['coding', 'programming', 'developer', 'javascript', 'python']
  },
  {
    id: 'shopping',
    name: 'Shopping Assistant',
    description: agentDescriptions.shopping,
    avatar: '/avatars/shopping_agent/shopping.webp',
    keywords: ['shopping', 'products', 'buy', 'purchase', 'deals', 'reviews', 'compare prices']
  }
];

function AgentSelection() {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentStandingPoseUrl, setCurrentStandingPoseUrl] = useState<string | null>(null);
  const [loadedStandingPoseImages, setLoadedStandingPoseImages] = useState<Set<string>>(new Set());
  const [isCurrentPoseLoading, setIsCurrentPoseLoading] = useState(true);

  const navigate = useNavigate();

  const filteredAgents = useMemo(() => {
    const query = searchQuery.toLowerCase();
    return agents.filter((agent) =>
      agent.name.toLowerCase().includes(query) ||
      agent.description.toLowerCase().includes(query) ||
      (agent.keywords?.some((kw) => kw.toLowerCase().includes(query)))
    );
  }, [searchQuery]);

  useEffect(() => {
    const preloadImages = async () => {
      const newLoadedImages = new Set<string>();
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
            resolve(standingPosePath);
          };
        });
      });

      await Promise.all(imagePromises);
      setLoadedStandingPoseImages(newLoadedImages);
      
      // Update current standing pose after preloading
      if (filteredAgents.length > 0) {
        const agentFolder = filteredAgents[selectedIndex].id + '_agent';
        const standingPosePath = `/avatars/${agentFolder}/standing_pose.webp`;
        setCurrentStandingPoseUrl(standingPosePath);
        setIsCurrentPoseLoading(!newLoadedImages.has(standingPosePath));
      } else {
        setCurrentStandingPoseUrl(null);
        setIsCurrentPoseLoading(false);
      }
    };

    preloadImages();
  }, [filteredAgents, selectedIndex]); // Keep both dependencies

  const rotateLeft = () => {
    setSelectedIndex((prev) => (prev - 1 + filteredAgents.length) % filteredAgents.length);
  };

  const rotateRight = () => {
    setSelectedIndex((prev) => (prev + 1) % filteredAgents.length);
  };

  const rotation = filteredAgents.length > 0
    ? 270 - (selectedIndex * (360 / filteredAgents.length))
    : 0;

  // Search box to be rendered in Navbar
  const searchBox = (
    <input
      type="text"
      className="agent-search-box"
      placeholder="Search agents..."
      value={searchQuery}
      onChange={e => setSearchQuery(e.target.value)}
      style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid #ccc', minWidth: 180 }}
    />
  );

  return (
    <>
      <Navbar showHomeLink={true} showAgentSelectionLink={false} searchBox={searchBox} />
      <div className="app" style={{ marginTop: '90px' }}>
        <h1>Select Your Agent</h1>
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
            {filteredAgents.map((agent, index) => {
              const angle = (360 / filteredAgents.length) * index + rotation;
              const x = 350 * Math.cos((angle * Math.PI) / 180);
              const y = 350 * Math.sin((angle * Math.PI) / 180);
              return (
                <div
                  key={agent.id}
                  className={`avatar-wrapper ${selectedIndex === index ? 'active-avatar' : ''}`}
                  style={{ transform: `translate(${x}px, ${y}px)` }}
                  onClick={() => setSelectedIndex(index)}
                >
                  <img src={agent.avatar} alt={agent.name} className="avatar" />
                  <span>{agent.name}</span>
                </div>
              );
            })}
          </div>

          {filteredAgents.length > 0 && (
            <div className="preview-card">
              <h2 className="preview-name">{filteredAgents[selectedIndex].name}</h2>
              <img
                src={filteredAgents[selectedIndex].avatar}
                alt={filteredAgents[selectedIndex].name}
                className="preview-avatar"
              />
              <p>Click "Details" to view this agent's full description and capabilities.</p>
              <button onClick={() => navigate('/details', { state: { agent: filteredAgents[selectedIndex] } })}>
                Details
              </button>
            </div>
          )}
        </div>

        {filteredAgents.length > 0 && (
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