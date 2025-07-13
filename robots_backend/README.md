# 🤖 Robots-AI Backend

FastAPI-based backend for the Robots-AI multi-agent platform. This backend provides RESTful APIs for 7 specialized AI agents, file processing capabilities, and real-time chat functionality with multimodal support.

## 🏗️ Architecture

- **Framework**: FastAPI with Python 3.11
- **LLM**: Google Gemini 2.5 Flash Lite Preview
- **Agent Framework**: LangGraph 0.2.52
- **Tools**: Composio for external integrations, AI Horde for image generation
- **File Processing**: OCR, PDF parsing, document analysis with multimodal support
- **Mapping**: OpenStreetMap and OpenRouteService integration

## 🚀 Quick Start

### Prerequisites
- Python 3.11
- Conda (recommended)

### Environment Setup
Create a `.env` file with the following variables:
```env
GOOGLE_API_KEY=your_google_api_key
COMPOSIO_API_KEY=your_composio_api_key
AI_Horde_API_KEY=your_ai_horde_api_key
HeiGIT_API_KEY=your_openrouteservice_api_key
```

### Installation
```bash
pip install -r requirements.txt
```

### Running the Backend
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

## 🤖 Available Agents

### 1. Coding Agent (`/coding`)
- **Capabilities**: Code generation, debugging, code review, file operations
- **Tools**: Code interpreter, search, file operations via Composio
- **Use Case**: Programming assistance and technical support

### 2. Finance Agent (`/finance`)
- **Capabilities**: Investment analysis, market research, financial planning
- **Tools**: Financial data, search, market analysis via Composio
- **Use Case**: Financial planning and investment guidance

### 3. News Agent (`/news`)
- **Capabilities**: News aggregation, analysis, current events
- **Tools**: News APIs, search via Composio
- **Use Case**: Current events and trend analysis

### 4. Real Estate Agent (`/realestate`)
- **Capabilities**: Property search, market insights, location analysis
- **Tools**: Search APIs, mapping tools (OSM/ORS)
- **Use Case**: Property investment and market analysis

### 5. Travel Agent (`/travel`)
- **Capabilities**: Trip planning, recommendations, route optimization
- **Tools**: Search APIs, mapping tools (OSM/ORS)
- **Use Case**: Travel planning and booking assistance

### 6. Image Generator (`/image`)
- **Capabilities**: AI image creation, editing, multimodal processing
- **Tools**: AI Horde image generation, multimodal support
- **Use Case**: Creative design and image manipulation

### 7. Shopping Agent (`/shopping`)
- **Capabilities**: Product search, price comparison, shopping assistance
- **Tools**: Shopping APIs, product databases via Composio
- **Use Case**: Shopping assistance and deal hunting

## 🔌 API Endpoints

### Main Chat Endpoint
```http
POST /chat
Content-Type: application/json
Authorization: Bearer your_token

{
  "message": "Hello, can you help me with coding?",
  "agent_id": "coding",
  "conversation_id": "optional_conversation_id",
  "user_name": "John",
  "file_content": "optional_file_content",
  "session_id": "optional_session_id"
}
```

### File Upload
```http
POST /files/upload
Content-Type: multipart/form-data

file: [binary file data]
conversation_id: "optional_conversation_id"
```

### Agent-Specific Endpoints
Each agent has its own endpoint:
- `POST /coding/ask`
- `POST /finance/ask`
- `POST /news/ask`
- `POST /realestate/ask`
- `POST /travel/ask`
- `POST /image/ask`
- `POST /shopping/ask`

### Health Check
```http
GET /health
```

### Root Endpoint
```http
GET /
```

## 📁 Project Structure

```
robots_backend/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── .composio.lock            # Composio tool lock file
├── agent_coding.py           # Coding agent implementation
├── agent_finance.py          # Finance agent implementation
├── agent_news.py             # News agent implementation
├── agent_realestate.py       # Real estate agent implementation
├── agent_travel.py           # Travel agent implementation
├── agent_image_generator.py  # Image generation agent
├── agent_shopping.py         # Shopping agent implementation
├── agents_system_prompts.py  # System prompts for all agents
├── tools.py                  # Shared tools (image generation)
├── file_processor.py         # File processing logic
├── file_upload.py           # File upload handling
├── ors_tools.py             # OpenRouteService tools
├── osm_tools.py             # OpenStreetMap tools
├── uploaded_files/          # User uploaded files directory
└── README_FILE_PROCESSING.md # File processing documentation
```

## 🛠️ Key Features

### Multimodal Support
- **Image Processing**: Agents can process images sent via URLs
- **File Upload**: Support for PDF, images, spreadsheets, text files, Word documents
- **OCR**: Automatic text extraction from images and documents
- **Content Analysis**: Extracted content is included in agent conversations

### Mapping Integration
- **OpenStreetMap Tools**: Geocoding, routing, POI search, bounding box search
- **OpenRouteService Tools**: Advanced routing, isochrones, elevation data
- **Real-time Data**: Live mapping and location services

### File Processing
- **Multiple Formats**: PDF, DOCX, XLSX, images, text files
- **Content Extraction**: Automatic text and metadata extraction
- **Error Handling**: Robust error handling for various file types
- **Storage**: Files stored in `uploaded_files/` directory

### Conversation Management
- **Session Persistence**: LangGraph memory for conversation history
- **Thread Management**: Unique conversation IDs for each chat session
- **State Management**: Proper state handling across agent interactions

## 🔧 Configuration

### CORS Settings
Configured for development:
```python
allow_origins=[
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://localhost:4173",  # Vite preview
    "http://127.0.0.1:4173"
]
```

### Security
- **Bearer Token Authentication**: All endpoints require authentication
- **File Validation**: Uploaded files are validated for type and size
- **Error Handling**: Comprehensive error handling with user-friendly messages

## 🚨 Troubleshooting

### Common Issues

1. **API Key Errors**
   ```
   Error: Invalid API key
   Solution: Check your .env file and API key validity
   ```

2. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'langgraph'
   Solution: Install dependencies with pip install -r requirements.txt
   ```

3. **CORS Errors**
   ```
   CORS error in browser
   Solution: Check CORS_ORIGINS configuration in main.py
   ```

4. **File Upload Issues**
   ```
   File upload fails
   Solution: Check uploaded_files/ directory permissions
   ```

5. **Image Processing Errors**
   ```
   Image processing fails
   Solution: Check AI Horde API key and network connectivity
   ```

### Debug Mode
Enable debug logging:
```bash
uvicorn main:app --reload --log-level debug
```

## 🔒 Security

### API Security
- All endpoints require Bearer token authentication
- File uploads are validated for type and size
- CORS is properly configured for development

### Environment Variables
- Never commit `.env` files to version control
- Use environment variables for all API keys
- Rotate API keys regularly

### File Security
- Uploaded files are stored in a dedicated directory
- File types are validated before processing
- Content extraction is performed securely

## 📈 Performance

### Optimization Tips
1. **Use async/await** for I/O operations
2. **Implement caching** for frequently accessed data
3. **Monitor memory usage** for large file processing
4. **Use connection pooling** for external API calls

### Scaling
- Use multiple workers with uvicorn
- Implement load balancing
- Consider using Redis for session storage
- Use CDN for static file serving

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

---

**Backend API for Robots-AI Multi-Agent Platform** 