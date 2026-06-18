import React, { useState } from 'react';
import axios from "axios";
import { Link } from "react-router-dom";
import { User, Sun, Moon, LogOut, Menu, X, FileText, MessageSquare, Code, MessageCircle, Video } from 'lucide-react';
import { useTheme } from './ThemeContext.jsx';

export default function Navbar() {
  const { theme, toggleTheme, isDark } = useTheme();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);



  const styles = {
    nav: {
      backgroundColor: isDark ? '#1f2937' : '#ffffff',
      borderBottomColor: isDark ? '#374151' : '#e5e7eb'
    },
    text: {
      color: isDark ? '#d1d5db' : '#4b5563'
    },
    hoverBg: isDark ? '#374151' : '#f9fafb'
  };

  const logout = async () => {
  try {
    const res = await axios.post(
      "http://localhost:3000/logout",
      {},
      { withCredentials: true }
    );

    if (res.status === 200) {
      window.location.href = "http://localhost:5173";
    }
  } catch (err) {
    console.error("Logout failed", err);
  }
};

  return (
    <nav 
      className="fixed top-0 left-0 w-full z-50 shadow-sm border-b transition-colors duration-200"
      style={styles.nav}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <a className="flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 transition-all duration-200 shadow-md hover:shadow-lg">
              <User size={20} style={{ color: '#ffffff', strokeWidth: 2 }} />
            </a>
          </div>

          <div className="hidden lg:flex items-center space-x-10">
            <Link to="/" className="flex items-center space-x-2 px-4 py-2 rounded-lg">
              <FileText size={16} />
              <span className="font-medium text-sm">Documents</span>
            </Link>
            <Link to="/chatbot" className="flex items-center space-x-2 px-4 py-2 rounded-lg">
              <MessageSquare size={16} />
              <span className="font-medium text-sm">AI Assistant</span>
            </Link>
            <Link to="/editor" className="flex items-center space-x-2 px-4 py-2 rounded-lg">
              <Code size={16} />
              <span className="font-medium text-sm">Code Editor</span>
            </Link>
            <Link to="/chat" className="flex items-center space-x-2 px-4 py-2 rounded-lg">
              <MessageCircle size={16} />
              <span className="font-medium text-sm">Chat</span>
            </Link>
            <a
              href="#video-call"
              className="flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200"
              style={{ color: styles.text.color }}
            >
              <Video size={16} />
              <span className="font-medium text-sm">Video Call</span>
            </a>
          </div>

          <div className="hidden lg:flex items-center space-x-2">
            <a
              onClick={toggleTheme}
              className="flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-200"
              style={{ color: styles.text.color }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = styles.hoverBg}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              {isDark ? (
                <Sun size={20} style={{ strokeWidth: 2 }} />
              ) : (
                <Moon size={20} style={{ strokeWidth: 2 }} />
              )}
            </a>
            <button 
              className="flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200"
              style={{ color: styles.text.color }}
              onClick={logout}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = styles.hoverBg}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              <LogOut size={16} />
              <span className="font-medium text-sm">Logout</span>
            </button>
          </div>

          <div className="flex lg:hidden items-center space-x-2">
            <a
              onClick={toggleTheme}
              className="flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-200"
              style={{ color: styles.text.color }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = styles.hoverBg}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              {isDark ? (
                <Sun size={20} style={{ strokeWidth: 2 }} />
              ) : (
                <Moon size={20} style={{ strokeWidth: 2 }} />
              )}
            </a>
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 rounded-lg transition-colors duration-200"
              style={{ color: styles.text.color }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = styles.hoverBg}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              {isMobileMenuOpen ? (
                <X size={24} style={{ strokeWidth: 2 }} />
              ) : (
                <Menu size={24} style={{ strokeWidth: 2 }} />
              )}
            </button>
          </div>
        </div>

        {isMobileMenuOpen && (
          <div 
            className="lg:hidden py-4 z-50 space-y-1 border-t"
            style={{ borderTopColor: isDark ? '#374151' : '#e5e7eb' }}
          >
            <Link to="/" className="flex items-center space-x-3 px-4 py-3 rounded-lg">
              <FileText size={20} />
              <span className="font-medium">Documents</span>
            </Link>
            <Link to="/chatbot" className="flex items-center space-x-3 px-4 py-3 rounded-lg">
              <MessageSquare size={20} />
              <span className="font-medium">AI Assistant</span>
            </Link>
            <Link to="/editor" className="flex items-center space-x-3 px-4 py-3 rounded-lg">
              <Code size={20} />
              <span className="font-medium">Code Editor</span>
            </Link>
            <Link to="/chat" className="flex items-center space-x-3 px-4 py-3 rounded-lg">
              <MessageCircle size={20} />
              <span className="font-medium">Chat</span>
            </Link>
            <a
              href="#video-call"
              className="flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200"
              style={{ color: styles.text.color }}
            >
              <Video size={20} />
              <span className="font-medium">Video Call</span>
            </a>

            <button 
              className="flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 w-full"
              style={{ color: styles.text.color }}
              onClick={logout}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = styles.hoverBg}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              <LogOut size={20} />
              <span className="font-medium">Logout</span>
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}