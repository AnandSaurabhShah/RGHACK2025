"use client";
import { useState, useCallback, useEffect, useRef } from "react";
import { useDropzone } from "react-dropzone";
import { FileText, UploadCloud, Send, Bot, User } from "lucide-react";

interface ChatMessage {
  content: string;
  isUser: boolean;
}

export default function Page() {
  const [jobRole, setJobRole] = useState("Software Engineer");
  const [result, setResult] = useState<{
    score: number;
    enhanced: string;
    skills: string[];
    original: string;
    job_role: string;
  } | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const jobRoles = [
    "Data Scientist", "Software Engineer", "DevOps Engineer",
    "Web Developer", "Machine Learning Engineer", "Data Analyst",
    "Cloud Engineer", "Full Stack Developer"
  ];

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setIsProcessing(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("job_role", jobRole);

    try {
      const response = await fetch("http://localhost:5000/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Processing failed");
      }
      
      const data = await response.json();
      setResult(data);
      setChatHistory([]);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error processing file");
    } finally {
      setIsProcessing(false);
    }
  }, [jobRole]);

  const handleChatSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!chatInput.trim() || !result) return;

    const userMessage = chatInput;
    setChatHistory(prev => [...prev, { content: userMessage, isUser: true }]);
    setChatInput("");

    try {
      const response = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: result.original,
          message: userMessage
        })
      });

      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      
      setChatHistory(prev => [
        ...prev,
        { content: data.response || "No answer found", isUser: false }
      ]);
    } catch (err) {
      setChatHistory(prev => [
        ...prev,
        { content: "Error getting response. Please try again.", isUser: false }
      ]);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
    maxSize: 5 * 1024 * 1024,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <FileText className="text-blue-600" />
            AI Resume Analyzer
          </h1>
          <select
            value={jobRole}
            onChange={(e) => setJobRole(e.target.value)}
            className="px-4 py-2 border rounded-lg bg-white shadow-sm"
          >
            {jobRoles.map((role) => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div {...getRootProps()} className={`mb-8 p-8 border-2 border-dashed rounded-xl text-center cursor-pointer transition-colors
          ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-blue-400"}`}>
          <input {...getInputProps()} />
          <div className="space-y-4">
            <UploadCloud className="mx-auto h-12 w-12 text-gray-400" />
            <h2 className="text-xl font-semibold">
              {isDragActive ? "Drop PDF here" : "Drag resume PDF here"}
            </h2>
            <p className="text-gray-500">PDF files only (max 5MB)</p>
          </div>
        </div>

        {result && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-white p-6 rounded-xl shadow-sm">
                <h3 className="text-lg font-semibold mb-4">Original Content</h3>
                <div className="text-gray-600 whitespace-pre-wrap max-h-96 overflow-y-auto">
                  {result.original}
                </div>
              </div>

              <div className="bg-white p-6 rounded-xl shadow-sm">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold">Enhanced Resume</h3>
                  <div className={`px-3 py-1 rounded-full text-sm 
                    ${result.score >= 8 ? "bg-green-100 text-green-800" : 
                       result.score >= 6 ? "bg-yellow-100 text-yellow-800" : 
                       "bg-red-100 text-red-800"}`}>
                    {result.score}/10 for {result.job_role}
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium mb-2">Matched Skills:</h4>
                    <div className="flex flex-wrap gap-2">
                      {result.skills.map((skill) => (
                        <span key={skill} className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="text-gray-800 whitespace-pre-wrap max-h-96 overflow-y-auto">
                    {result.enhanced}
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Bot className="text-green-600" />
                Resume Chat Assistant
              </h3>
              
              <div className="h-96 overflow-y-auto mb-4 bg-gray-50 rounded-lg p-4">
                {chatHistory.map((msg, i) => (
                  <div key={i} className={`flex gap-3 mb-4 ${msg.isUser ? "justify-end" : "justify-start"}`}>
                    {!msg.isUser && <Bot className="text-gray-500 mt-1" size={20} />}
                    <div className={`max-w-3xl p-3 rounded-lg ${msg.isUser ? "bg-blue-100" : "bg-gray-100"}`}>
                      {msg.content}
                    </div>
                    {msg.isUser && <User className="text-gray-500 mt-1" size={20} />}
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              <form onSubmit={handleChatSubmit} className="flex gap-2">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about this resume..."
                  className="flex-1 p-2 border rounded-lg"
                  disabled={!result}
                />
                <button
                  type="submit"
                  disabled={!result || !chatInput.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:bg-gray-400"
                >
                  <Send size={18} />
                </button>
              </form>
            </div>
          </>
        )}

        {isProcessing && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="bg-white p-6 rounded-lg flex items-center gap-4 shadow-xl">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="text-gray-700">Analyzing Resume...</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}