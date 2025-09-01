import React, { useState } from 'react';
import './DeepSearchContainer.css';

interface DeepSearchContainerProps {
  sources: string[];
}

const DeepSearchContainer: React.FC<DeepSearchContainerProps> = ({ sources }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="deep-search-container">
      <div
        className="deep-search-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="deep-search-title">
          🔍 Deep Search
        </span>
        <span className="deep-search-count">
          {sources.length} sources
        </span>
        <span className="deep-search-toggle">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {isExpanded && (
        <div className="deep-search-content">
          <div className="deep-search-sources">
            {sources.map((source, index) => (
              <a
                key={index}
                href={source}
                target="_blank"
                rel="noopener noreferrer"
                className="deep-search-link"
              >
                {source}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DeepSearchContainer;