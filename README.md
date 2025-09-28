# 🤖 Robots-AI: Multi-Agent AI Assistant Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A sophisticated multi-agent AI system built with React frontend and Python backend, featuring specialized AI agents for various tasks including coding, finance, news, real estate, travel, image generation, and shopping assistance.

## 🌍 Travel Agent Demo

Check out a short video demo of the Travel Agent in action:
https://youtu.be/dLcbg4htcJ8

## 🏡 Real Estate Agent Demo

Watch a quick demo of the Real Estate Agent in action:
https://youtu.be/yrBJ0CRmyEU

## 🎮 Games Agent Demo

Watch a quick demo of the Games Agent in action:
https://youtu.be/w6gwGUEF7i0

## 💰 Finance Agent with Deep Search Demo

Watch the AI-powered Finance Agent with advanced deep search capabilities in action:
https://youtu.be/bel9mymvYCg

## Agent-switching System Demo

Watch a quick demo of the new powerful agent-switching system in action:
https://youtu.be/Z1i5hmBJz-I

## Coding Agent Demo

Watch a quick demo of the (Agent Mode) coding Agent in action:
https://youtu.be/j2UX84jdfz8

## ✨ Features

### 🤖 Specialized AI Agents
- **Coding Agent**: Programming assistance, debugging, and code reviews
- **Finance Agent**: Investment advice, financial planning, and market analysis
- **News Agent**: Real-time news aggregation and analysis
- **Real Estate Agent**: Property search, market insights, and investment guidance
- **Travel Agent**: Trip planning, recommendations, and travel assistance
- **Image Generator**: AI-powered image creation and editing
- **Shopping Agent**: Product search, price comparison, and shopping assistance
- **Games Agent**: Interactive chess gameplay with strategy and analysis

### 🎨 Modern UI/UX
- **Responsive Design**: Works seamlessly on desktop
- **Real-time Chat**: Interactive chat interface with typing indicators
- **File Upload**: Support for images, documents, and various file types
- **Agent Avatars**: Dynamic pose animations for each agent
- **Personalization**: Agents address users by name for personalized experience

### 🔧 Technical Features
- **Multi-modal Support**: Text and image processing capabilities
- **File Processing**: OCR, PDF parsing, document analysis
- **Memory System**: Conversation history and context retention
- **Real-time Chat**: Interactive chat interface with typing indicators
- **Interactive Games**: Real-time chess gameplay with move validation
- **Service Worker**: Cached assets for faster loading

## ⚠️ Current Limitations

### Image Generation
- **Processing Time**: Image generation takes 2-10 minutes depending on the AI Horde queue and model selection
- **Queue-based System**: Processing time varies based on server load and model popularity

### Speech Features
- **Speech-to-Text**: Not yet integrated
- **Speech-to-Speech**: Not yet integrated
- **Voice Features**: Text-based communication only

### Real Estate Search
- **Geographic Coverage**: Real estate active listings search is limited to USA properties only

## 🚀 Quick Start

### Prerequisites
- Python 3.11
- Node.js 18+
- Conda (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/wiss84/robots-ai.git
   cd robots-ai
   ```

2. **Create and activate conda environment**
   ```bash
   conda create -n robots_app python=3.11 nodejs
   conda activate robots_app
   ```

3. **Install backend dependencies**
   ```bash
   cd robots_backend
   pip install -r requirements.txt
   ```

4. **Install frontend dependencies**
   ```bash
   cd robots_frontend
   npm install
   ```

5. **Set up environment variables**
   ```bash
   # In robots_backend folder, create .env file
   cp .env.example .env
   # Edit .env with your API keys
   ```

6. **Set up Supabase database**
> See [How to Get Your Free Supabase Project URL and Anon Key (frontend README)](robots_frontend/README.md#-how-to-get-your-free-supabase-project-url-and-anon-key)
   - Create tables for conversations and messages
   - Enable Row Level Security (RLS)
   - Set up access policies

7. **Start the backend**
   ```bash
   cd robots_backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
   ```

8. **Start the frontend**
   ```bash
   cd robots_frontend
   npm run dev
   ```

9. **Open your browser**
   Navigate to `http://localhost:5173`

## 🔑 Environment Variables

Create a `.env` file in the `robots_backend` directory:

> **Need help finding and registering for free API keys?**
> See [How to Get Free API Keys (backend README)](robots_backend/README.md#-how-to-get-free-api-keys)

```env
# Google AI API (free with limited refreshable usage per day)
GOOGLE_API_KEY=your_google_api_key_here

# Composio MCP API (for search tools, free with limited refreshable usage per month)
COMPOSIO_API_KEY=your_composio_api_key_here
COMPOSIO_USER_ID='The email you signed up with on composio'

# LangSmith (if you want to observe for debugging)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY='your_langchain_api_key'
LANGCHAIN_PROJECT='your_project_name'

# image generation (100% free, but has queue depends on the model you use.)
AI_Horde_API_KEY='your_ai_horde_api_key'

# openrouteservice endpoints for maps tools(free with limited refreshable usage per day)
HeiGIT_API_KEY='your_heigit_api_key'

# RealtyUS API for real estate listings (USA only, free with limited usage)
RAPIDAPI_KEY='your_rapidapi_key'

# Supabase URL & service role key (found under your supabase's project : API keys, Data API)
SUPABASE_URL='your_supabase_url'
SUPABASE_SERVICE_ROLE_KEY='your_supabase_service_role_key'

# App Settings
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## Doker installation (optional)
If Docker isn't installed:
1. Download from: https://docs.docker.com/desktop/install/windows-install/
2. Install and start Docker Desktop (after successful installation and restart you might get a message to update or install your wsl(windows subsystem linux)):
3. Open your terminal or powershell and run:
wsl --update # to update (if it exist)
wsl --install # to install (if it doesn't exist)

4. Restart docker desktop
5. Open a terminal or powershell and run:
cd Desktop\robots-ai (or wherever you cloned it)
docker-compose up --build
6. Run your local server on the browser: http://localhost:5173

## 🏗️ Project Structure

```
robots-ai/
├── README.md                    # This file
├── robots_backend/              # Python FastAPI backend
│   ├── main.py                 # Main application entry point
│   ├── requirements.txt        # Python dependencies
│   ├── agent_*.py             # Individual agent implementations
│   ├── tools.py               # Shared tools and utilities
│   ├── RealtyUS_tools.py      # Real estate API tools
│   ├── file_processor.py      # File processing logic
│   ├── summarize.py           # Conversation summarization endpoint
│   └── uploaded_files/        # User uploaded files
├── robots_frontend/            # React TypeScript frontend
│   ├── package.json           # Node.js dependencies
│   ├── src/                   # Source code
│   │   ├── components/        # React components
│   │   ├── pages/            # Page components
│   │   ├── hooks/            # Custom React hooks
│   │   └── utils/            # Utility functions
│   └── public/               # Static assets
└── docs/                     # Documentation
```

## 🤖 Agent Capabilities

### Coding Agent
- Code generation and debugging
- Programming language support
- Code review and optimization
- Technical documentation

### Finance Agent
- Investment analysis
- Market research
- Financial planning
- Portfolio management

### News Agent
- Real-time news aggregation
- Topic-specific news filtering
- News analysis and summaries
- Trend identification

### Real Estate Agent
- Property search assistance (USA only)
- Real-time rental and sale listings via RealtyUS API
- Market analysis and investment guidance
- Location insights with interactive maps
- Points of interest search around properties
- Property type filtering (apartments, houses, condos, etc.)
- Display inline maps with property markers
- Display inline images of properties

### Travel Agent
- Trip planning
- Destination recommendations
- Flights and hotel search
- Itinerary creation
- Display inline maps for hotels or most interesting places
- Display inline images the hotels or places

### Image Generator
- AI-powered image creation
- Style transfer
- Image editing
- Creative design assistance

### Shopping Agent
- Product search
- Price comparison
- Shopping recommendations
- Deal hunting

### Games Agent
- Interactive chess gameplay with real-time board updates
- Move validation and legal move checking
- Strategy explanations and move analysis
- Natural language chess communication
- Game state tracking (checkmate, stalemate, draw detection)


## 🛠️ Development

### Quick Start (Using .bat file instead of running each terminal manually)
Create a `start_app.bat` file in the root directory:

```batch
@echo off
echo Starting backend...

CALL "%USERPROFILE%\anaconda3\Scripts\activate.bat" robots_app
start cmd /k "CALL %USERPROFILE%\anaconda3\Scripts\activate.bat robots_app && cd robots_backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug"

timeout /t 5
echo Starting frontend...

cd robots_frontend
start cmd /k "npm run dev"

timeout /t 5
start "" "http://localhost:5173/"
```

Then simply run: `start_app.bat`

### Manual Development

#### Backend Development
```bash
cd robots_backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

#### Frontend Development
```bash
cd robots_frontend
npm run dev
```

### Building for Production
```bash
# Frontend
cd robots_frontend
npm run build

# Backend
cd robots_backend
pip install -r requirements.txt
```

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🤝 Contributing

We welcome contributions to Robots-AI! Whether you want to add new agents, improve existing features, or fix bugs, your help is appreciated.

### 🚀 How to Contribute

#### 1. **Fork the Repository**
```bash
# Click "Fork" button on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/robots-ai.git
cd robots-ai
```

#### 2. **Set Up Development Environment**
```bash
# Create and activate conda environment
conda create -n robots_app python=3.11 nodejs
conda activate robots_app

# Install backend dependencies
cd robots_backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../robots_frontend
npm install
```

#### 3. **Create a Feature Branch**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

#### 4. **Make Your Changes**
- **Backend**: Add new agents in `robots_backend/agent_*.py`
- **Frontend**: Update components in `robots_frontend/src/components/`
- **Documentation**: Update README files as needed

#### 5. **Test Your Changes**
```bash
# Test backend
cd robots_backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# Test frontend
cd robots_frontend
npm run dev
```

#### 6. **Commit and Push**
```bash
git add .
git commit -m "Add: brief description of your changes"
git push origin feature/your-feature-name
```

#### 7. **Open a Pull Request**
- Go to your fork on GitHub
- Click "New Pull Request"
- Describe your changes clearly

### 🎯 Areas for Contribution

#### **New AI Agents**
- Add specialized agents for different domains
- Implement new tools and capabilities
- Create agent-specific system prompts

#### **Frontend Improvements**
- Add new UI components
- Improve user experience
- Add new features (themes, settings, etc.)

#### **Backend Enhancements**
- Add new API endpoints
- Improve file processing
- Add new integrations

#### **Documentation**
- Improve README files
- Add code comments
- Create tutorials

#### **Bug Fixes**
- Fix reported issues
- Improve error handling
- Performance optimizations

### 📋 Contribution Guidelines

#### **Code Style**
- **Python**: Follow PEP 8 guidelines
- **TypeScript**: Use consistent formatting
- **Comments**: Add clear comments for complex logic

#### **Commit Messages**
```bash
# Good commit messages
git commit -m "Add: new finance analysis agent"
git commit -m "Fix: resolve CORS issue in file upload"
git commit -m "Update: improve agent response formatting"
```

#### **Pull Request Template**
When creating a PR, include:
- **Description** of what you changed
- **Testing** you performed
- **Screenshots** (if UI changes)
- **Related issues** (if any)

### 🏷️ Issue Labels

- `enhancement` - New features
- `bug` - Bug fixes
- `documentation` - Documentation updates
- `good first issue` - Good for beginners
- `help wanted` - Looking for contributors

### 🎉 Recognition

Contributors will be:
- **Listed** in the README
- **Mentioned** in release notes
- **Credited** in the project

### 📞 Need Help?

- **Questions**: Open a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Email**: wissammetawee84@outlook.com

**Thank you for contributing to Robots-AI!** 🚀

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Citation

If you use this project in your research or work, please cite it as:

```bibtex
@software{robots_ai_2025,
  title={Robots-AI: Multi-Agent AI Assistant Platform},
  author={Wissam Metawee},
  year={2025},
  url={https://github.com/wiss84/robots-ai},
  license={MIT}
}
```

Or simply include a link to this repository in your acknowledgments.

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for the agent framework
- [LangChain](https://github.com/langchain-ai/langchain) for LLM integration
- [Google AI](https://ai.google.dev/) for the Gemini model
- [Composio](https://composio.dev/) for tool integrations
- [OpenStreetMap](https://www.openstreetmap.org/) for map data and routing services
- [HeiGIT](https://heigit.org/) for OpenRouteService API providing routing and geocoding
- [RealtyUS](https://rapidapi.com/ntd119/api/realty-us) for real estate listings data
- [AI Horde](https://aihorde.net/) for free AI image generation services
- [React](https://reactjs.org/) for the frontend framework
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/wiss84/robots-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/wiss84/robots-ai/discussions)
- **Email**: wissammetawee84@outlook.com

## 🔄 Version History

- **v1.0.0** - Initial release with 7 specialized agents

**Made with ❤️ by [Wissam Metawee]**

*Transform your workflow with intelligent AI agents!* 
