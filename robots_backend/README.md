# 🤖 Robots-AI Backend

FastAPI-based backend for the Robots-AI multi-agent platform. This backend provides RESTful APIs for 7 specialized AI agents, file processing capabilities, and real-time chat functionality.

## 🏗️ Architecture

- **Framework**: FastAPI with Python 3.11
- **LLM**: Google Gemini 2.5 Flash Lite
- **Agent Framework**: LangGraph 0.2.52
- **Tools**: Composio for external integrations
- **Database**: Supabase (PostgreSQL)
- **File Processing**: OCR, PDF parsing, document analysis

## 🚀 Quick Start

### Prerequisites
- Python 3.11
- Conda (recommended)

## 🤖 Available Agents

### 1. Coding Agent (`/coding`)
- **Capabilities**: Code generation, debugging, code review
- **Tools**: Code interpreter, search, file operations
- **Use Case**: Programming assistance and technical support

### 2. Finance Agent (`/finance`)
- **Capabilities**: Investment analysis, market research
- **Tools**: Financial data, market analysis
- **Use Case**: Financial planning and investment guidance

### 3. News Agent (`/news`)
- **Capabilities**: News aggregation, analysis
- **Tools**: News APIs, search
- **Use Case**: Current events and trend analysis

### 4. Real Estate Agent (`/realestate`)
- **Capabilities**: Property search, market insights
- **Tools**: Real estate APIs, location data
- **Use Case**: Property investment and market analysis

### 5. Travel Agent (`/travel`)
- **Capabilities**: Trip planning, recommendations
- **Tools**: Travel APIs, booking systems
- **Use Case**: Travel planning and booking assistance

### 6. Image Generator (`/image`)
- **Capabilities**: AI image creation, editing
- **Tools**: Image generation APIs
- **Use Case**: Creative design and image manipulation

### 7. Shopping Agent (`/shopping`)
- **Capabilities**: Product search, price comparison
- **Tools**: Shopping APIs, product databases
- **Use Case**: Shopping assistance and deal hunting

### 8. More Agents will be added in near future

### Main Chat Endpoint
```http
POST /chat
Content-Type: application/json

{
  "message": "Hello, can you help me with coding?",
  "agent_id": "coding",
  "conversation_id": "optional_conversation_id",
  "user_name": "John",
  "file_content": "optional_file_content"
}
```

### File Upload
```http
POST /upload
Content-Type: multipart/form-data

file: [binary file data]
```

### Health Check
```http
GET /health
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

## 📁 Project Structure

```
robots_backend/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── agent_coding.py           # Coding agent implementation
├── agent_finance.py          # Finance agent implementation
├── agent_news.py             # News agent implementation
├── agent_realestate.py       # Real estate agent implementation
├── agent_travel.py           # Travel agent implementation
├── agent_image_generator.py  # Image generation agent
├── agent_shopping.py         # Shopping agent implementation
├── agents_system_prompts.py  # System prompts for all agents
├── tools.py                  # Shared tools and utilities
├── file_processor.py         # File processing logic
├── file_upload.py           # File upload handling
├── ors_tools.py             # OpenRouteService tools
├── osm_tools.py             # OpenStreetMap tools
├── uploaded_files/          # User uploaded files directory
└── README_FILE_PROCESSING.md # File processing documentation
```

## 🛠️ Development

### Running in Development Mode
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### Running in Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing
```bash
# Run tests (if you have pytest installed)
pytest

# Check API health
curl http://localhost:8000/health
```

## 🔧 Configuration

### CORS Settings
Configure allowed origins in your `.env` file:
```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://yourdomain.com
```

### Memory Management
- Short term conversation history is stored in LangGraph memory session
- long term conversation history is stored in Supabase (PostgreSQL)
- File uploads are stored in `uploaded_files/` directory
- Consider implementing cleanup for old files

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
   Solution: Check CORS_ORIGINS in .env file
   ```

4. **File Upload Issues**
   ```
   File upload fails
   Solution: Check uploaded_files/ directory permissions
   ```

### Debug Mode
Enable debug logging:
```bash
uvicorn main:app --reload --log-level debug
```

## 🔒 Security

### API Security
- All endpoints require authentication (Bearer token)
- File uploads are validated for type and size
- CORS is properly configured

### Environment Variables
- Never commit `.env` files to version control
- Use `.env.example` as a template
- Rotate API keys regularly

### File Security
- Uploaded files are stored in a dedicated directory
- File types are validated before processing

## 📈 Performance

### Optimization Tips
1. **Use async/await** for I/O operations
2. **Implement caching** for frequently accessed data
3. **Use connection pooling** for database connections
4. **Monitor memory usage** for large file processing

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