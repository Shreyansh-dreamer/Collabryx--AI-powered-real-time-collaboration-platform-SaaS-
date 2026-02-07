import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {MessageCircle,Plus,Send,Loader2,Wrench,ChevronLeft,ChevronRight,Sparkles,Bot,User,AlertCircle} from 'lucide-react';

const api = axios.create({
  baseURL: 'http://localhost:8000/chat',
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
  
  const [interruptData, setInterruptData] = useState(null);
  const [interruptType, setInterruptType] = useState(null);

  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null);

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

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [currentThreadId]);

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

  
  const createNewChat = () => {
    const id = generateId();
    setThreads((p) => [id, ...p].slice(0, MAX_THREADS));
    setCurrentThreadId(id);
    setMessages([]);
    setThreadNames((p) => ({ ...p, [id]: 'New Conversation' }));
    setInterruptData(null);
    setInterruptType(null);
  };

  const loadConversation = async (id) => {
    setCurrentThreadId(id);
    if (window.innerWidth < 768) setSidebarOpen(false);
    setInterruptData(null);
    setInterruptType(null);
    
    try {
      const res = await api.get(`/threads/${id}`);
      const msgs = res.data?.messages || [];
      setMessages(msgs);
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

  
  const handleInterrupt = (data) => {
    console.log("Interrupt received:", data);
    setInterruptData(data);
    setInterruptType(data.type);
    setIsProcessing(false);
    
    if (data.type === 'GMAIL_AUTH_REQUIRED') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message || 'Gmail authentication required. Click the link below to authorize.'
      }]);
    } else {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message || 'Please provide additional information.'
      }]);
    }
  };

  const handleInterruptResponse = async (userResponse) => {
    if (!currentThreadId || !interruptType) return;

    setInput('');
    setInterruptData(null);
    setInterruptType(null);
    setIsProcessing(true);

    try {
      if (interruptType === 'GMAIL_AUTH_REQUIRED' && userResponse.gmail_access_token) {
        await api.post('/resume', {
          thread_id: currentThreadId,
          state_update: {
            gmail_access_token: userResponse.gmail_access_token,
            gmail_token_expiry: userResponse.gmail_token_expiry
          }
        });
      } else {
        const userMsg = { role: 'user', content: userResponse };
        setMessages(prev => [...prev, userMsg]);
        await api.post('/resume', {
          thread_id: currentThreadId,
          user_input: userResponse
        });
      }
      
      streamChat();
    } catch (err) {
      console.error("Failed to resume after interrupt:", err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, there was an error processing your response.'
      }]);
      setIsProcessing(false);
    }
  };

  
  const streamChat = () => {
    if (!currentThreadId) return;
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setIsProcessing(true);
    const es = new EventSource(`http://localhost:8000/chat/stream?thread_id=${currentThreadId}`);
    eventSourceRef.current = es;
    
    es.addEventListener('message', (e) => {
      try {
        const data = JSON.parse(e.data);
        
        if (data.role && data.content) {
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg?.role === 'assistant' && data.role === 'assistant') {
              return [...prev.slice(0, -1), { role: 'assistant', content: data.content }];
            }
            return [...prev, { role: data.role, content: data.content }];
          });
        }
      } catch (err) {
        console.error("Error parsing message event:", err);
      }
    });

    es.addEventListener('interrupt', (e) => {
      try {
        const data = JSON.parse(e.data);
        handleInterrupt(data);
        es.close();
        eventSourceRef.current = null;
      } catch (err) {
        console.error("Error parsing interrupt event:", err);
      }
    });

    es.addEventListener('end', () => {
      setIsProcessing(false);
      setCurrentTool(null);
      es.close();
      eventSourceRef.current = null;
    });

    es.addEventListener('error', (err) => {
      console.error("EventSource error:", err);
      setIsProcessing(false);
      setCurrentTool(null);
      es.close();
      eventSourceRef.current = null;
    });
  };


  const handleSendMessage = async () => {
    if (!input.trim() || !currentThreadId) return;
    if (interruptType) {
      await handleInterruptResponse(input);
      return;
    }

    const userMsg = { role: 'user', content: input };
    setMessages((p) => [...p, userMsg]);
    const tempInput = input;
    setInput('');
    setIsProcessing(true);

    try {
      if (messages.length === 0) {
        setThreadNames((p) => ({
          ...p,
          [currentThreadId]: generateThreadName(tempInput)
        }));
      }

      await api.post('/resume', {
        thread_id: currentThreadId,
        user_input: tempInput
      });

      streamChat();
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, there was an error processing your message.'
      }]);
      setIsProcessing(false);
    }
  };


  useEffect(() => {
    const handleAuthCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      
      if (code) {
        try {
          const res = await api.get(`/gmail/auth/callback?code=${code}`);
          if (res.data.gmail_access_token) {
            await handleInterruptResponse({
              gmail_access_token: res.data.gmail_access_token,
              gmail_token_expiry: res.data.gmail_token_expiry
            });
          }
          window.history.replaceState({}, document.title, window.location.pathname);
        } catch (err) {
          console.error("Auth callback error:", err);
        }
      }
    };
    
    handleAuthCallback();
  }, []);

  
  const renderInterruptUI = () => {
    if (!interruptData) return null;
    switch (interruptType) {
      case 'GMAIL_AUTH_REQUIRED':
        return (
          <div className={`p-4 rounded-xl border mb-4 ${
            isDark ? 'bg-yellow-900/20 border-yellow-700' : 'bg-yellow-50 border-yellow-200'
          }`}>
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium mb-2">Gmail Authorization Required</p>
                <a
                  href={`${interruptData.auth_start_endpoint}?thread_id=${currentThreadId}`}
                  className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Authorize Gmail Access
                </a>
              </div>
            </div>
          </div>
        );

      case 'USER_CHOICE':
        return (
          <div className={`p-4 rounded-xl border mb-4 ${
            isDark ? 'bg-blue-900/20 border-blue-700' : 'bg-blue-50 border-blue-200'
          }`}>
            <p className="font-medium mb-3">{interruptData.message}</p>
            <div className="space-y-2">
              {interruptData.options?.map((opt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleInterruptResponse(opt.username || String(opt.index))}
                  className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                    isDark 
                      ? 'bg-gray-800 hover:bg-gray-700 border border-gray-700' 
                      : 'bg-white hover:bg-gray-50 border border-gray-200'
                  }`}
                >
                  <span className="font-medium">{opt.username}</span>
                  {opt.name && <span className={`ml-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>({opt.name})</span>}
                </button>
              ))}
            </div>
          </div>
        );

      case 'EMAIL_BODY_CONFIRM':
        return (
          <div className={`p-4 rounded-xl border mb-4 ${
            isDark ? 'bg-blue-900/20 border-blue-700' : 'bg-blue-50 border-blue-200'
          }`}>
            <p className="font-medium mb-2">Email Preview</p>
            <div className={`p-3 rounded-lg mb-3 ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <pre className="whitespace-pre-wrap text-sm">{interruptData.email_body}</pre>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleInterruptResponse('yes')}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Send Email
              </button>
              <button
                onClick={() => {
                  setInterruptType('EMAIL_BODY_EDIT');
                }}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  isDark 
                    ? 'bg-gray-700 hover:bg-gray-600 text-white' 
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
                }`}
              >
                Edit
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div
      className={`flex h-full pt-[72px] w-full overflow-hidden
      ${isDark
        ? 'bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800 text-gray-100'
        : 'bg-gradient-to-br from-gray-50 via-blue-50/30 to-gray-50 text-gray-900'
      }`}
    >
      <div className={`${
       sidebarOpen
      ? 'w-64 sm:w-72 lg:w-80'
      : 'w-0'
      } transition-all duration-300 ease-in-out border-r flex flex-col overflow-hidden ${
        isDark ? 'bg-gray-900/95 backdrop-blur-xl border-gray-700/50' : 'bg-white/95 backdrop-blur-xl border-gray-200/50'
      }`}>
        <div className={`p-6 border-b flex-shrink-0 ${isDark ? 'border-gray-700/50' : 'border-gray-200/50'}`}>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-xl ${isDark ? 'bg-gradient-to-br from-blue-500 to-purple-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'} shadow-lg`}>
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-xl">AI Assistant</h1>
              </div>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className={`p-2 rounded-lg transition-colors ${
                isDark ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-600'
              }`}
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
                  className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all ${
                    currentThreadId === threadId
                      ? isDark
                        ? 'bg-gradient-to-r from-blue-600/20 to-purple-600/20 text-white border border-blue-500/30'
                        : 'bg-gradient-to-r from-blue-500/10 to-blue-600/10 text-blue-700 border border-blue-200'
                      : isDark
                      ? 'hover:bg-gray-800 text-gray-300'
                      : 'hover:bg-gray-50 text-gray-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <MessageCircle className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate font-medium">
                      {threadNames[threadId] || 'New Conversation'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col w-screen pt-18">
        <div className={`border-b px-4 sm:px-6 py-4 sm:py-5 flex-shrink-0 ${isDark ? 'border-gray-700/50 bg-gray-900/50' : 'border-gray-200/50 bg-white/50'}`}>
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className={`p-2 rounded-lg transition-colors ${
                  isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-100'
                }`}
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            )}
            <div className={`p-2 rounded-lg ${isDark ? 'bg-gradient-to-br from-purple-500/20 to-pink-500/20' : 'bg-gradient-to-br from-purple-100 to-pink-100'}`}>
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Multi Utility Chatbot</h2>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center py-12">
                <div className="text-center">
                  <div className={`w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-6 ${
                    isDark ? 'bg-gradient-to-br from-blue-500/20 to-purple-500/20' : 'bg-gradient-to-br from-blue-100 to-purple-100'
                  }`}>
                    <Sparkles className="w-10 h-10" />
                  </div>
                  <h3 className="text-2xl font-bold mb-3">Start a conversation</h3>
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isDark ? 'bg-gradient-to-br from-blue-500 to-purple-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'
                    }`}>
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-2xl rounded-2xl px-5 py-3 ${
                      msg.role === 'user'
                        ? isDark
                          ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white'
                          : 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
                        : isDark
                        ? 'bg-gray-800 text-gray-100'
                        : 'bg-white text-gray-900'
                    }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{renderMessageWithLinks(msg.content)}</p>
                  </div>
                  {msg.role === 'user' && (
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isDark ? 'bg-gradient-to-br from-emerald-500 to-teal-600' : 'bg-gradient-to-br from-emerald-500 to-teal-600'
                    }`}>
                      <User className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              ))
            )}
            
            {renderInterruptUI()}
            
            {currentTool && (
              <div className="flex justify-start gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  isDark ? 'bg-gradient-to-br from-blue-500 to-purple-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'
                }`}>
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div className={`flex items-center gap-3 px-5 py-3 rounded-2xl ${
                  isDark ? 'bg-gray-800' : 'bg-white'
                }`}>
                  <Wrench className="w-4 h-4 animate-pulse text-blue-500" />
                  <span className="text-sm">Using {currentTool}...</span>
                </div>
              </div>
            )}
            
            {isProcessing && !currentTool && (
              <div className="flex justify-start gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  isDark ? 'bg-gradient-to-br from-blue-500 to-purple-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'
                }`}>
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div className={`flex items-center gap-3 px-5 py-3 rounded-2xl ${
                  isDark ? 'bg-gray-800' : 'bg-white'
                }`}>
                  <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className={`border-t p-6 flex-shrink-0 ${isDark ? 'border-gray-700/50 bg-gray-900/50' : 'border-gray-200/50 bg-white/50'}`}>
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                placeholder={interruptType ? "Type your response..." : "Type your message..."}
                disabled={!currentThreadId}
                className={`flex-1 px-5 py-4 rounded-xl border-2 outline-none transition-all ${
                  isDark
                    ? 'bg-gray-800 border-gray-700 focus:border-blue-500 text-white'
                    : 'bg-white border-gray-200 focus:border-blue-500 text-gray-900'
                } disabled:opacity-50`}
              />
              <button
                onClick={handleSendMessage}
                disabled={!input.trim() || isProcessing || !currentThreadId}
                className={`px-6 py-4 rounded-xl font-semibold transition-all flex items-center gap-2 ${
                  isDark
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500'
                    : 'bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700'
                } text-white disabled:opacity-50`}
              >
                <Send className="w-5 h-5" />
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;