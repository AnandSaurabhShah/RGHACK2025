"use client";
import { useState } from 'react';
import { useDropzone } from 'react-dropzone';

export default function UploadPage() {
  const [result, setResult] = useState<{ score?: number; feedback?: string }>({});
  const [isProcessing, setIsProcessing] = useState(false);

  // Simplified onDrop function without useCallback
  async function onDrop(acceptedFiles: File[]) {
    console.log("onDrop triggered with files:", acceptedFiles);
    const file = acceptedFiles[0];
    if (!file) return;

    // Basic file type validation
    if (file.type !== "application/pdf") {
      setResult({ feedback: "Only PDF files are allowed." });
      return;
    }

    setIsProcessing(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:5000/resume', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) throw new Error(`Processing failed: ${response.status}`);
      const data = await response.json();
      setResult(data);
      console.log("Upload successful", data);
    } catch (error: any) {
      console.error("Upload error:", error);
      setResult({ feedback: error.message || 'Error processing resume' });
    } finally {
      setIsProcessing(false);
      console.log("onDrop finished");
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false,
  });

  return (
    <div className="container">
      <h1>OpenResume</h1>
      
      <div className="upload-section">
        <h2>Import data from an existing resume</h2>
        
        <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
          <input {...getInputProps()} />
          <p>Browse a pdf file or drop it here</p>
          <small>File data is used locally and never leaves your browser</small>
          <button className="browse-button">Browse file</button>
        </div>

        <div className="or-divider">Or</div>
        
        <button className="create-button">
          Don't have a resume yet? Create from scratch
        </button>
      </div>

      {isProcessing && <p>Processing resume...</p>}
      
      {result.score !== undefined && (
        <div className="result-section">
          <h3>Resume Analysis Result</h3>
          <p>Score: {result.score}</p>
          {result.feedback && <p>Feedback: {result.feedback}</p>}
        </div>
      )}

      <style jsx>{`
        .container {
          max-width: 800px;
          margin: 2rem auto;
          padding: 2rem;
        }
        .upload-section {
          border: 2px dashed #ccc;
          padding: 2rem;
          text-align: center;
        }
        .dropzone {
          padding: 2rem;
          cursor: pointer;
          background: #f8f9fa;
        }
        .dropzone.active {
          background: #e9ecef;
          border-color: #0d6efd;
        }
        .browse-button {
          margin-top: 1rem;
          padding: 0.5rem 1rem;
          background: #0d6efd;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }
        .or-divider {
          margin: 2rem 0;
          position: relative;
          color: #666;
        }
        .create-button {
          width: 100%;
          padding: 1rem;
          background: transparent;
          border: 1px solid #0d6efd;
          color: #0d6efd;
          cursor: pointer;
        }
        .result-section {
          margin-top: 2rem;
          padding: 1rem;
          background: #f8f9fa;
        }
      `}</style>
    </div>
  );
}
