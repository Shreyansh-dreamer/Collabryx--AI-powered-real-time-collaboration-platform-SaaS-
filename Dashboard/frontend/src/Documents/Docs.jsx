import React, { useEffect, useState } from 'react';
import axios from "axios";
import { Upload, File, X, Check, FileText, Image, FileSpreadsheet, FileCode, Zap, Shield, Clock, Layers } from 'lucide-react';

export default function UserProfilePage() {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [email, setEmail] = useState("");
  const [photos, setPhotos] = useState([]);
  const [org, setOrg] = useState("");
  const [user, setUser] = useState("");

  const fetchUser = async () => {
  try {
    const res = await axios.get("http://localhost:3000/whoAmI", {
      withCredentials: true,
    });
    const data = res.data;
    setUser(data.username);
    setEmail(data.email);
    setOrg(data.org);
    setPhotos(data.photos || []);
  } catch (err) {
    console.error(
      "Fetch user failed:",
      err.response?.data || err.message
    );
  }
};

  useEffect(() => {
    fetchUser();
  }, []);

  const getInitials = (name) => {
    if (!name) return "";
    const parts = name.trim().split(" ");
    if (parts.length === 1) return parts[0][0].toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
   };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = async (files) => {
    const pdfFiles = Array.from(files).filter(file => file.type === "application/pdf");
    if (pdfFiles.length === 0) {
        alert("Only PDF files are allowed");
        return;
    }
    const oversized = pdfFiles.find(file => file.size > 10 * 1024 * 1024);
    if (oversized) {
        alert(`File too large: ${oversized.name} (max 10 MB)`);
        return;
    }
    const newFiles = pdfFiles.map(file => ({
      id: crypto.randomUUID(),
      name: file.name,
      size: `${(file.size / 1024 / 1024).toFixed(2)} MB`,
      uploadedAt: new Date().toLocaleTimeString(),
    }));
    setUploadedFiles(prev => [...prev, ...newFiles]);
    // Upload to backend
    for (let file of pdfFiles) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("org", org); 
        try {
        const res = await axios.post("http://localhost:8000/upload",
          formData,{ headers: { "Content-Type": "multipart/form-data" } }
        );
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload failed");
        alert(`Uploaded: ${file.name}\n${data.message}`);
        } catch (err) {
        console.error(err);
        alert("Upload failed: " + err.message);
        }
    }
};


  const removeFile = (id) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== id));
  };

  const getFileIcon = (fileName) => {
    const ext = fileName.split('.').pop().toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(ext)) return Image;
    if (['xls', 'xlsx', 'csv'].includes(ext)) return FileSpreadsheet;
    if (['js', 'jsx', 'ts', 'tsx', 'html', 'css', 'json'].includes(ext)) return FileCode;
    return FileText;
  };

  const features = [
    {
      icon: Zap,
      title: 'Instant Processing',
      desc: 'Files processed in milliseconds'
    },
    {
      icon: Shield,
      title: 'Bank-Grade Security',
      desc: 'AES-256 encryption at rest'
    },
    {
      icon: Clock,
      title: 'Version Control',
      desc: 'Automatic backup & history'
    },
    {
      icon: Layers,
      title: 'Smart Organization',
      desc: 'AI-powered categorization'
    }
  ];

  return (
    <div className="min-h-screen min-w-screen pt-18 bg-gradient-to-br from-gray-50 via-gray-50 to-blue-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        {/* User Profile Section */}
        <div className="relative bg-white dark:bg-gray-800 rounded-3xl shadow-lg overflow-hidden mb-6 lg:mb-8">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-indigo-500/10 to-purple-500/10 dark:from-blue-500/5 dark:via-indigo-500/5 dark:to-purple-500/5"></div>
          <div className="relative p-6 sm:p-8">
            <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
              {/* Avatar */}
              <div className="relative">
                <div className="w-24 h-24 sm:w-28 sm:h-28 lg:w-32 lg:h-32 rounded-full overflow-hidden shadow-xl flex-shrink-0 bg-gradient-to-br from-blue-500 via-indigo-600 to-purple-600 flex items-center justify-center">
                    {photos && photos.length > 0 ? (
                        <img
                        src={photos}
                        alt="Profile"
                        className="w-full h-full object-cover"
                        />
                    ) : (
                        <span className="text-white text-3xl sm:text-4xl font-semibold">
                        {getInitials(user)}
                        </span>
                    )}
                </div>
                <div className="absolute -bottom-1 -right-1 top-1 w-6 h-6 bg-green-500 rounded-full border-4 border-white dark:border-gray-800"></div>
              </div>
              
              {/* Profile Info */}
              <div className="flex-1 text-center md:text-left">
                <div className="flex items-center justify-center md:justify-start gap-2 mb-2">
                  <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">{user}</h1>
                  <div className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-semibold rounded-full">
                    PRO
                  </div>
                </div>
                <p className="text-gray-600 dark:text-gray-300 mb-1 text-lg">{email}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 text-xl">{org}</p>
            
                <div className="flex flex-wrap gap-3 justify-center md:justify-start">
                  <button className="px-4 py-2 bg-blue-100 dark:bg-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                    View Profile
                  </button>
                  <button className="px-4 py-2 bg-gray-100 dark:bg-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                    Settings
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6 lg:gap-8 lg:pt-5">
          {/* Document Upload Section */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-3xl shadow-lg p-6 sm:p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">Upload Center</h2>
                <div className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs font-semibold rounded-full flex items-center gap-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  Online
                </div>
              </div>
              
              {/* Upload Area */}
              <div
                className={`relative border-2 border-dashed rounded-2xl transition-all ${
                  dragActive 
                    ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20' 
                    : 'border-gray-300 dark:border-gray-600 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700/50 dark:to-gray-800/50 hover:border-gray-400 dark:hover:border-gray-500'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  multiple={false}
                  accept="application/pdf"
                  onChange={handleChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="flex flex-col items-center justify-center py-16 px-6">
                  <div className={`w-20 h-20 rounded-2xl flex items-center justify-center mb-4 transition-all transform ${
                    dragActive ? 'bg-gradient-to-br from-blue-500 to-indigo-600 scale-110' : 'bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-600 dark:to-gray-700'
                  }`}>
                    <Upload className={`w-10 h-10 ${dragActive ? 'text-white' : 'text-gray-600 dark:text-gray-300'}`} />
                  </div>
                  <p className="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-2 text-center">
                    {dragActive ? 'Drop files to upload' : 'Drag & drop files here'}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 text-center">
                    or <span className="text-blue-600 dark:text-blue-400 font-medium cursor-pointer">click to browse</span>
                  </p>
                  <div className="mt-4">
                    <h4 className="font-medium mb-2">Selected PDF:</h4>
                    <ul>
                        {uploadedFiles.map(file => (
                        <li key={file.id}>{file.name} ({(file.size/1024/1024).toFixed(2)} MB)</li>
                        ))}
                    </ul>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-center">
                    <span className="px-3 py-1 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs rounded-full border border-gray-200 dark:border-gray-600">PDF</span>
                    <span className="px-3 py-1 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs rounded-full border border-gray-200 dark:border-gray-600">DOC</span>
                  </div>
                </div>
              </div>

              {/* Uploaded Files List */}
              {uploadedFiles.length > 0 && (
                <div className="mt-8">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Files ({uploadedFiles.length})
                    </h3>
                    <button
                      onClick={() => setUploadedFiles([])}
                      className="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium"
                    >
                      Clear all
                    </button>
                  </div>
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {uploadedFiles.map((file) => {
                      const FileIcon = getFileIcon(file.name);
                      return (
                        <div
                          key={file.id}
                          className="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700/50 dark:to-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600 transition-all group hover:shadow-md"
                        >
                          <div className="flex items-center gap-4 flex-1 min-w-0">
                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-md">
                              <FileIcon className="w-6 h-6 text-white" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">
                                {file.name}
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                <p className="text-xs text-gray-500 dark:text-gray-400">{file.size}</p>
                                <span className="text-gray-400 dark:text-gray-500">•</span>
                                <p className="text-xs text-gray-500 dark:text-gray-400">{file.uploadedAt}</p>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                              <Check className="w-5 h-5 text-green-600 dark:text-green-400" />
                            </div>
                            <button
                              onClick={() => removeFile(file.id)}
                              className="w-8 h-8 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all"
                            >
                              <X className="w-5 h-5 text-red-600 dark:text-red-400" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Features */}
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-3xl shadow-lg p-6 sm:p-8">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-6">Platform Features</h3>
              <div className="space-y-4">
                {features.map((feature, idx) => (
                  <div 
                    key={idx} 
                    className="group p-4 rounded-xl bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700/50 dark:to-gray-800/50 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600 transition-all cursor-pointer hover:shadow-md"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                        <feature.icon className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
                          {feature.title}
                        </h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {feature.desc}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-3xl shadow-lg p-6 text-white lg:hidden">
              <h3 className="text-lg font-bold mb-2">Storage Capacity</h3>
              <div className="flex items-end gap-2 mb-3">
                <span className="text-3xl font-bold">2.4</span>
                <span className="text-lg opacity-80 mb-1">/ 10 GB</span>
              </div>
              <div className="w-full h-2 bg-white/20 rounded-full overflow-hidden mb-3">
                <div className="h-full bg-white rounded-full" style={{ width: '24%' }}></div>
              </div>
              <button className="w-full py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors backdrop-blur-sm">
                Upgrade Storage
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}