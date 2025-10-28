import React, { useState } from 'react';
import { Upload, File, X, Check, AlertCircle } from 'react-icons/fi';
import api from '../api';
import '../css/DocumentUpload.css';

const DocumentUpload = ({ projectType, projectId, onUploadComplete }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [extractTags, setExtractTags] = useState(true);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validate file type
      const allowedTypes = ['.pdf', '.docx', '.doc', '.txt'];
      const fileExt = '.' + file.name.split('.').pop().toLowerCase();

      if (!allowedTypes.includes(fileExt)) {
        setUploadStatus({
          type: 'error',
          message: `Unsupported file type. Allowed: ${allowedTypes.join(', ')}`
        });
        return;
      }

      setSelectedFile(file);
      setUploadStatus(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setUploadStatus(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      if (projectType) {
        formData.append('project_type', projectType);
      }
      if (projectId) {
        formData.append('project_id', projectId.toString());
      }
      formData.append('auto_process', 'true');
      formData.append('extract_tags', extractTags.toString());

      const response = await api.post('/ai/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setUploadStatus({
        type: 'success',
        message: `Successfully uploaded ${selectedFile.name}. Processing in background...`,
        data: response.data
      });

      setSelectedFile(null);

      if (onUploadComplete) {
        onUploadComplete(response.data);
      }

    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to upload document'
      });
    } finally {
      setUploading(false);
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setUploadStatus(null);
  };

  return (
    <div className="document-upload-container">
      <div className="upload-header">
        <Upload size={20} />
        <h3>Upload Document</h3>
      </div>

      <div className="upload-body">
        {!selectedFile ? (
          <label className="file-drop-area">
            <input
              type="file"
              accept=".pdf,.docx,.doc,.txt"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <div className="drop-icon">
              <File size={48} />
            </div>
            <p className="drop-text">
              Click to select or drag and drop
            </p>
            <p className="drop-hint">
              Supported: PDF, DOCX, TXT
            </p>
          </label>
        ) : (
          <div className="selected-file">
            <div className="file-info">
              <File size={24} />
              <div className="file-details">
                <p className="file-name">{selectedFile.name}</p>
                <p className="file-size">
                  {(selectedFile.size / 1024).toFixed(2)} KB
                </p>
              </div>
            </div>
            <button
              className="clear-file-btn"
              onClick={handleClearFile}
              disabled={uploading}
            >
              <X size={18} />
            </button>
          </div>
        )}

        {selectedFile && (
          <div className="upload-options">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={extractTags}
                onChange={(e) => setExtractTags(e.target.checked)}
                disabled={uploading}
              />
              <span>Auto-extract tags and metadata using AI</span>
            </label>
          </div>
        )}

        {uploadStatus && (
          <div className={`upload-status ${uploadStatus.type}`}>
            {uploadStatus.type === 'success' ? (
              <Check size={20} />
            ) : (
              <AlertCircle size={20} />
            )}
            <span>{uploadStatus.message}</span>
          </div>
        )}

        {selectedFile && (
          <button
            className="upload-btn"
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? 'Uploading...' : 'Upload Document'}
          </button>
        )}
      </div>
    </div>
  );
};

export default DocumentUpload;
