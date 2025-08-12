import React, { useRef, useState } from 'react';
import './FileUpload.css';
import { FiPaperclip } from 'react-icons/fi';

interface FileUploadProps {
  conversationId?: string;
  onUploadSuccess?: (fileInfo: any) => void;
  onFileSelected?: (file: File) => void;
  workspaceUpload?: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({ 
  conversationId, 
  onUploadSuccess, 
  onFileSelected,
  workspaceUpload = false 
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    if (onFileSelected) {
      onFileSelected(file);
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('workspace_upload', workspaceUpload.toString());
      if (conversationId) formData.append('conversation_id', conversationId);
      
      const res = await fetch('http://localhost:8000/project/files/upload', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      setUploading(false);
      
      // Check if file processing was successful
      if (data.success === false) {
        setError(data.error || 'File processing failed');
        return;
      }
      
      if (onUploadSuccess) onUploadSuccess(data);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
      setUploading(false);
    }
  };

  return (
    <div className="file-upload-root">
      <input
        ref={fileInputRef}
        type="file"
        style={{ display: 'none' }}
        onChange={handleFileChange}
        accept=".pdf,.txt,.csv,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.bmp,.webp,.svg"
      />
      <button
        type="button"
        className="file-upload-btn"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        aria-label="Attach File"
      >
        {uploading ? 'Uploading...' : <FiPaperclip size={22} color="#00bcd4" />}
      </button>
      {fileName && !uploading && (
        <div className="file-upload-status">
          <div className="file-upload-success">
            <span className="success-icon">✓</span>
            <span className="success-text">File uploaded successfully</span>
          </div>
        </div>
      )}
      {error && <span className="file-upload-error">{error}</span>}
    </div>
  );
};

export default FileUpload;
