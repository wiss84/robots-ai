# File Processing Capabilities

### Supported File Types
- **Text Files**: `.txt`, `.md` - Direct text extraction
- **Documents**: `.pdf`, `.docx`, `.doc` - Text extraction with formatting
- **Spreadsheets**: `.csv`, `.xlsx`, `.xls` - Tabular data with column analysis
- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp` - OCR text extraction + image analysis
- **Data Files**: `.json`, `.xml` - Structured data parsing

### Features
- ✅ **Automatic Content Extraction** - No manual processing required
- ✅ **OCR for Images** - Extract text from images, screenshots, documents
- ✅ **PDF Text Extraction** - Multi-page PDF support
- ✅ **Spreadsheet Analysis** - Column headers, data types, row counts
- ✅ **Context Integration** - File content automatically added to agent context
- ✅ **Error Handling** - Graceful handling of unsupported or corrupted files

## 🔧 Installation

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH environment variable
```

## 📁 How It Works

### File Upload Flow
1. **User uploads file** → Frontend sends to `/files/upload`
2. **Backend processes file** → `FileProcessor` extracts content
3. **Content is returned** → Includes extracted text, metadata, and processing status
4. **Agent receives content** → File content added to conversation context
5. **Agent responds** → Can analyze, summarize, or answer questions about the file

### Example API Response
```json
{
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "file_path": "/path/to/uploaded_files/document.pdf",
  "extracted_content": "This is the text content extracted from the PDF...",
  "metadata": {
    "file_type": "pdf",
    "pages": 3,
    "has_text": true
  },
  "success": true
}
```

## 🎯 Usage Examples

### Text Files
- Upload `.txt` or `.md` files
- Agent can analyze, summarize, or answer questions about the content

### PDF Documents
- Upload reports, articles, or any PDF
- Agent extracts text from all pages
- Can answer questions about the document content

### Images with Text
- Upload screenshots, scanned documents, or images with text
- OCR extracts text automatically
- Agent can read and analyze the text content

### Spreadsheets
- Upload CSV or Excel files
- Agent gets column headers, data types, and row counts
- Can analyze trends, patterns, or answer data questions

### JSON/XML Data
- Upload configuration files or data exports
- Agent can parse and explain the structure
- Useful for debugging or data analysis

## 🔍 Agent Capabilities

Once a file is uploaded, your agents can:
- **Summarize** the content
- **Answer questions** about the file
- **Extract key information** from documents
- **Analyze data** from spreadsheets
- **Explain** complex documents
- **Compare** multiple files
- **Generate insights** from the content

## 🛠️ Technical Details

### File Processing Pipeline
```python
# 1. File Upload
file_location = save_file(uploaded_file)

# 2. Content Extraction
extraction_result = file_processor.extract_content(file_location)

# 3. Context Integration
if extraction_result["content"]:
    agent_message += f"\n[Uploaded File Content:\n{extraction_result['content']}\n]"

# 4. Agent Processing
agent_response = agent_graph.invoke({"messages": [message]})
```

### Error Handling
- Unsupported file types return clear error messages
- Corrupted files are handled gracefully
- Processing errors are logged and reported to user

### Performance
- Large files are processed efficiently
- Memory usage is optimized
- Processing time scales with file size

## 🎉 Try It Out!

1. **Start your backend**: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
2. **Start your frontend**: `npm run dev`
3. **Upload any file** and ask questions about it
4. **Test different file types**

### Example Conversations
- "Upload this PDF and summarize the key points"
- "What does this spreadsheet tell us about sales trends?"
- "Can you extract the contact information from this image?"
- "Analyze this JSON configuration file for me"
