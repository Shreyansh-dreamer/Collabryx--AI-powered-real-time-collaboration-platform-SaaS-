import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {MessageCircle,Plus,Send,Loader2,Wrench,ChevronLeft,ChevronRight,Sparkles,Bot,User} from 'lucide-react';

const api = axios.create({
  baseURL: '/chat',
  withCredentials: true
});


const Chatbot = ({ theme = 'light' }) => {
  const isDark = theme === 'dark';
  const MAX_THREADS = 10;

  const [threads, setThreads] = useState([]);
  const [currentThreadId, setCurrentThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [threadNames, setThreadNames] = useState({});
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentTool, setCurrentTool] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);


  useEffect(() => {
    if (threads.length === 0) createNewChat();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const handleResize = () => {
      setSidebarOpen(window.innerWidth >= 768);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);


  const generateId = () =>
    `thread-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  const generateThreadName = (msg) => {
    if (!msg) return 'New Conversation';
    const words = msg.split(' ').slice(0, 5).join(' ');
    return words.length > 40 ? words.slice(0, 40) + '…' : words;
  };

  const renderMessageWithLinks = (text) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.split(urlRegex).map((part, i) =>
      part.match(urlRegex) ? (
        <a
          key={i}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className={`underline font-medium ${
            isDark ? 'text-blue-400 ' : 'text-blue-600'
          }`}
        >
          {part}
        </a>
      ) : (
        <span key={i}>{part}</span>
      )
    );
  };

  /* -------------------- CHAT THREADS -------------------- */
  const createNewChat = () => {
    const id = generateId();
    setThreads((p) => [id, ...p].slice(0, MAX_THREADS));
    setCurrentThreadId(id);
    setMessages([]);
    setThreadNames((p) => ({ ...p, [id]: 'New Conversation' }));
  };

  const loadConversation = async (id) => {
    setCurrentThreadId(id);
    if (window.innerWidth < 768) setSidebarOpen(false);
    try {
      const res = await api.get(`/threads/${id}`);
      const msgs = res.data?.messages || [];
      setMessages(msgs);
      // Set thread name if not already set
      if (!threadNames[id] && msgs.length > 0) {
        setThreadNames((p) => ({
          ...p,
          [id]: generateThreadName(msgs.find(m => m.role === 'user')?.content || '')
        }));
      }
    } catch (err) {
      console.error("Failed to load thread messages:", err);
      setMessages([]);
    }
  };

  const handleBackendResponse = async (data) => {
    if (data?.type === 'AUTH_REQUIRED') {
      sessionStorage.setItem(
        'lg_resume',
        JSON.stringify(data.resume_payload)
      );
      window.location.href = data.auth_url;
      return;
    }
    if (data?.tool) {
      setCurrentTool(data.tool);
      return;
    }
    if (data?.error) {
      setMessages((p) => [
        ...p,
        { role: 'assistant', content: data.error }
      ]);
      setIsProcessing(false);
      return;
    }
    if (data?.messages) {
      setMessages((p) => [...p, ...data.messages]);
    }
    setCurrentTool(null);
    setIsProcessing(false);
  };

  const streamChat = (payload) => {
    setIsProcessing(true);
    const es = new EventSource("http://localhost:8000/chat/stream");
    let buffer = "";
    es.onmessage = (e) => {
      const evt = JSON.parse(e.data);
      if (evt.event === "on_llm_token") {
        buffer += evt.data.chunk;
        setMessages(p => {
          const last = p[p.length - 1];
          if (last?.role === 'assistant') {
            return [...p.slice(0, -1), { role: 'assistant', content: buffer }];
          }
          return [...p, { role: 'assistant', content: buffer }];
        });
      }
      if (evt.event === "on_tool_start") setCurrentTool(evt.name);
      if (evt.event === "on_tool_end") setCurrentTool(null);
      if (evt.event === "interrupt") {
        window.location.href = evt.data.auth_url;
        es.close();
      }
      if (evt.event === "end" || evt.event === "error") {
        setIsProcessing(false);
        es.close();
      }
    };
  };


  /* -------------------- SEND MESSAGE -------------------- */
  const handleSendMessage = () => {
    if (!input.trim() || !currentThreadId) return;
    const userMsg = { role: 'user', content: input };
    if (messages.length === 0) {
      setThreadNames((p) => ({
        ...p,
        [currentThreadId]: generateThreadName(input)
      }));
    }
    setMessages((p) => [...p, userMsg]);
    setInput('');
    setIsProcessing(true);
    streamChat({
      messages: [{ role: 'user', content: input }],
      thread_id: currentThreadId
    });
  };


  /* -------------------- RESUME AFTER AUTH -------------------- */
  useEffect(() => {
    const resume = async () => {
      const saved = sessionStorage.getItem('lg_resume');
      if (!saved) return;
      sessionStorage.removeItem('lg_resume');
      const payload = JSON.parse(saved);
      const res = await api.post('/resume', payload);
      handleBackendResponse(res.data);
    };
    resume();
  }, []);


  return (
    <div className={`flex h-screen overflow-hidden ${isDark ? 'bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800 text-gray-100' : 'bg-gradient-to-br from-gray-50 via-blue-50/30 to-gray-50 text-gray-900'}`}>
      <div className={`${
        sidebarOpen ? 'w-80' : 'w-0'
      } transition-all duration-300 ease-in-out border-r flex flex-col overflow-hidden ${
        isDark ? 'bg-gray-900/95 backdrop-blur-xl border-gray-700/50' : 'bg-white/95 backdrop-blur-xl border-gray-200/50'
      }`}>
        <div className="p-6 border-b flex-shrink-0 ${isDark ? 'border-gray-700/50' : 'border-gray-200/50'}">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-xl ${isDark ? 'bg-gradient-to-br from-blue-500 to-purple-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'} shadow-lg`}>
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-xl">AI Assistant</h1>
                <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                </p>
              </div>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className={`p-2 rounded-lg transition-colors ${
                isDark ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-600'
              }`}
              title="Close sidebar"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>
          
          <button
            onClick={createNewChat}
            className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-semibold transition-all shadow-lg hover:shadow-xl transform hover:scale-[1.02] ${
              isDark 
                ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white' 
                : 'bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white'
            }`}
          >
            <Plus className="w-5 h-5" />
            New Chat
          </button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto p-3">
          <div className="flex items-center justify-between px-2 py-2 mb-2">
            <p className={`text-xs font-bold uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              Recent Chats
            </p>
            <span className={`text-xs px-2 py-1 rounded-full ${
              isDark ? 'bg-gray-700 text-gray-400' : 'bg-gray-100 text-gray-600'
            }`}>
              {threads.length}/{MAX_THREADS}
            </span>
          </div>
          {threads.length === 0 ? (
            <div className={`px-4 py-8 text-center rounded-xl ${isDark ? 'bg-gray-800/50' : 'bg-gray-50'}`}>
              <MessageCircle className={`w-8 h-8 mx-auto mb-2 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
              <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                No conversations yet
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {threads.map((threadId) => (
                <button
                  key={threadId}
                  onClick={() => loadConversation(threadId)}
                  className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all group ${
                    currentThreadId === threadId
                      ? isDark
                        ? 'bg-gradient-to-r from-blue-600/20 to-purple-600/20 text-white border border-blue-500/30 shadow-lg'
                        : 'bg-gradient-to-r from-blue-500/10 to-blue-600/10 text-blue-700 border border-blue-200 shadow-md'
                      : isDark
                      ? 'hover:bg-gray-800 text-gray-300 border border-transparent'
                      : 'hover:bg-gray-50 text-gray-700 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <MessageCircle className={`w-4 h-4 flex-shrink-0 ${
                      currentThreadId === threadId 
                        ? 'text-blue-400' 
                        : isDark ? 'text-gray-500' : 'text-gray-400'
                    }`} />
                    <span className="truncate font-medium">
                      {threadNames[threadId] || 'New Conversation'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className={`p-4 border-t flex-shrink-0 ${isDark ? 'border-gray-700/50' : 'border-gray-200/50'}`}>
          <p className={`text-xs text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            Max {MAX_THREADS} conversations stored
          </p>
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <div className={`border-b px-4 sm:px-6 py-4 sm:py-5 flex-shrink-0 ${isDark ? 'border-gray-700/50 bg-gray-900/50 backdrop-blur-xl' : 'border-gray-200/50 bg-white/50 backdrop-blur-xl'} shadow-sm`}>
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className={`p-2 rounded-lg transition-colors ${
                  isDark ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-600'
                }`}
                title="Open sidebar"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            )}
            <div className={`p-2 rounded-lg ${isDark ? 'bg-gradient-to-br from-purple-500/20 to-pink-500/20' : 'bg-gradient-to-br from-purple-100 to-pink-100'}`}>
              <Bot className={`w-5 h-5 sm:w-6 sm:h-6 ${isDark ? 'text-purple-400' : 'text-purple-600'}`} />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="text-lg sm:text-xl font-bold truncate">Multi Utility Chatbot</h2>
              <p className={`text-xs sm:text-sm truncate ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Ask questions or use various tools
              </p>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div className="max-w-4xl mx-auto space-y-4 sm:space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center py-12">
                <div className="text-center max-w-md px-4">
                  <div className={`w-16 h-16 sm:w-20 sm:h-20 rounded-2xl flex items-center justify-center mx-auto mb-4 sm:mb-6 ${
                    isDark ? 'bg-gradient-to-br from-blue-500/20 to-purple-500/20' : 'bg-gradient-to-br from-blue-100 to-purple-100'
                  } shadow-xl`}>
                    <Sparkles className={`w-8 h-8 sm:w-10 sm:h-10 ${isDark ? 'text-blue-400' : 'text-blue-600'}`} />
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold mb-2 sm:mb-3">Start a conversation</h3>
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-2 sm:gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isDark ? 'bg-gradient-to-br from-blue-500 to-purple-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'
                    } shadow-lg`}>
                      <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] sm:max-w-2xl rounded-2xl px-4 sm:px-5 py-2.5 sm:py-3 shadow-md ${
                      msg.role === 'user'
                        ? isDark
                          ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white'
                          : 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
                        : isDark
                        ? 'bg-gray-800 text-gray-100 border border-gray-700/50'
                        : 'bg-white text-gray-900 border border-gray-200'
                    }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{renderMessageWithLinks(msg.content)}</p>
                  </div>
                  {msg.role === 'user' && (
                    <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isDark ? 'bg-gradient-to-br from-emerald-500 to-teal-600' : 'bg-gradient-to-br from-emerald-500 to-teal-600'
                    } shadow-lg`}>
                      <User className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                    </div>
                  )}
                </div>
              ))
            )}
            
            {currentTool && (
              <div className="flex justify-start gap-2 sm:gap-3">
                <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  isDark ? 'bg-gradient-to-br from-blue-500 to-purple-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'
                } shadow-lg`}>
                  <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                </div>
                <div className={`flex items-center gap-2 sm:gap-3 px-4 sm:px-5 py-2.5 sm:py-3 rounded-2xl shadow-md ${
                  isDark ? 'bg-gray-800 text-gray-300 border border-gray-700/50' : 'bg-white text-gray-700 border border-gray-200'
                }`}>
                  <Wrench className="w-4 h-4 animate-pulse text-blue-500" />
                  <span className="text-sm font-medium">Using {currentTool}...</span>
                </div>
              </div>
            )}
            
            {isProcessing && !currentTool && (
              <div className="flex justify-start gap-2 sm:gap-3">
                <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  isDark ? 'bg-gradient-to-br from-blue-500 to-purple-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'
                } shadow-lg`}>
                  <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                </div>
                <div className={`flex items-center gap-2 sm:gap-3 px-4 sm:px-5 py-2.5 sm:py-3 rounded-2xl shadow-md ${
                  isDark ? 'bg-gray-800 border border-gray-700/50' : 'bg-white border border-gray-200'
                }`}>
                  <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className={`border-t p-3 sm:p-4 md:p-6 flex-shrink-0 ${isDark ? 'border-gray-700/50 bg-gray-900/50 backdrop-blur-xl' : 'border-gray-200/50 bg-white/50 backdrop-blur-xl'} shadow-lg`}>
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-2 sm:gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                placeholder="Type your message..."
                disabled={!currentThreadId}
                className={`flex-1 px-4 sm:px-5 py-3 sm:py-4 rounded-xl border-2 outline-none transition-all shadow-sm text-sm sm:text-base ${
                  isDark
                    ? 'bg-gray-800 border-gray-700 focus:border-blue-500 text-white placeholder-gray-500'
                    : 'bg-white border-gray-200 focus:border-blue-500 text-gray-900 placeholder-gray-400'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              />
              <button
                onClick={handleSendMessage}
                disabled={!input.trim() || isProcessing || !currentThreadId}
                className={`px-4 sm:px-6 py-3 sm:py-4 rounded-xl font-semibold transition-all flex items-center gap-2 shadow-lg hover:shadow-xl transform hover:scale-[1.02] ${
                  isDark
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white'
                    : 'bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white'
                } disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none`}
              >
                <Send className="w-4 h-4 sm:w-5 sm:h-5" />
                <span className="hidden sm:inline">Send</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;