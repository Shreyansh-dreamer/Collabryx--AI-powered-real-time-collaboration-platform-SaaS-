import { useEffect, useState } from "react";
import io from "socket.io-client";
import Editor from "@monaco-editor/react";
import socket from '../Socket.jsx'

const App = ({ theme = "dark" }) => {
  const [joined, setJoined] = useState(false);
  const [roomId, setRoomId] = useState("");
  const [userName, setUserName] = useState("");
  const [language, setLanguage] = useState("javascript");
  const [code, setCode] = useState("// start code here");
  const [copySuccess, setCopySuccess] = useState("");
  const [users, setUsers] = useState([]);
  const [typing, setTyping] = useState("");
  const [editorTheme, setEditorTheme] = useState("vs-dark");

  const isDark = theme === "dark";

  useEffect(() => {
    socket.on("userJoined", (users) => {
      setUsers(users);
    });

    socket.on("codeUpdate", (newCode) => {
      setCode(newCode);
    });

    socket.on("userTyping", (user) => {
      setTyping(`${user.slice(0, 8)}... is Typing`);
      setTimeout(() => setTyping(""), 2000);
    });

    socket.on("languageUpdate", (newLanguage) => {
      setLanguage(newLanguage);
    });

    return () => {
      socket.off("userJoined");
      socket.off("codeUpdate");
      socket.off("userTyping");
      socket.off("languageUpdate");
    };
  }, []);

  useEffect(() => {
    const handleBeforeUnload = () => {
      socket.emit("leaveRoom");
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, []);

  const joinRoom = () => {
    if (roomId && userName) {
      socket.emit("join", { roomId, userName });
      setJoined(true);
    }
  };

  const leaveRoom = () => {
    socket.emit("leaveRoom");
    setJoined(false);
    setRoomId("");
    setUserName("");
    setCode("// start code here");
    setLanguage("javascript");
  };

  const copyRoomId = () => {
    navigator.clipboard.writeText(roomId);
    setCopySuccess("Copied!");
    setTimeout(() => setCopySuccess(""), 2000);
  };

  const handleCodeChange = (newCode) => {
    setCode(newCode);
    socket.emit("codeChange", { roomId, code: newCode });
    socket.emit("typing", { roomId, userName });
  };

  const handleLanguageChange = (e) => {
    const newLanguage = e.target.value;
    setLanguage(newLanguage);
    socket.emit("languageChange", { roomId, language: newLanguage });
  };

  const toggleEditorTheme = () => {
    setEditorTheme(prev => prev === "vs-dark" ? "light" : "vs-dark");
  };

  if (!joined) {
    return (
      <div className={`pt-10 min-h-screen min-w-screen transition-colors duration-300 ${isDark ? 'bg-gradient-to-br from-gray-900 via-slate-900 to-gray-900' : 'bg-gradient-to-br from-gray-50 via-blue-50 to-gray-50'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-20">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Side - Marketing Content */}
            <div className="space-y-8">
              <div className="space-y-4">
                <h1 className={`text-4xl sm:text-5xl lg:text-6xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  Code Together,
                  <span className="bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent"> In Real-Time</span>
                </h1>
                <p className={`text-lg sm:text-xl ${isDark ? 'text-gray-400' : 'text-gray-600'} max-w-xl`}>
                  Collaborate seamlessly with your team. Share code, sync changes instantly, and build amazing things together.
                </p>
              </div>

              {/* Features */}
              <div className="grid sm:grid-cols-2 gap-4">
                {[
                  { icon: '⚡', title: 'Lightning Fast', desc: 'Real-time synchronization' },
                  { icon: '🔒', title: 'Secure Rooms', desc: 'Private collaboration spaces' },
                  { icon: '🎨', title: 'Syntax Highlighting', desc: 'Multi-language support' },
                  { icon: '👥', title: 'Team Presence', desc: 'See who\'s coding with you' }
                ].map((feature, idx) => (
                  <div key={idx} className={`p-4 rounded-xl ${isDark ? 'bg-gray-800/50 border border-gray-700' : 'bg-white border border-gray-200'} backdrop-blur-sm transition-transform hover:scale-105`}>
                    <div className="text-2xl mb-2">{feature.icon}</div>
                    <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'} mb-1`}>{feature.title}</h3>
                    <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{feature.desc}</p>
                  </div>
                ))}
              </div>
            </div>


            <div className={`${isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-white border-gray-200'} backdrop-blur-xl border rounded-2xl p-8 shadow-2xl`}>
              <div className="space-y-6">
                <div className="text-center space-y-2">
                  <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl ${isDark ? 'bg-gradient-to-br from-blue-500 to-purple-600' : 'bg-gradient-to-br from-blue-600 to-purple-700'} mb-4`}>
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                  </div>
                  <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Join a Code Room</h2>
                  <p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Enter your details to start collaborating</p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                      Room ID
                    </label>
                    <input
                      type="text"
                      placeholder="Enter room ID"
                      value={roomId}
                      onChange={(e) => setRoomId(e.target.value)}
                      className={`w-full px-4 py-3 rounded-lg ${isDark ? 'bg-gray-900 border-gray-700 text-white placeholder-gray-500' : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400'} border focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none`}
                    />
                  </div>

                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                      Your Name
                    </label>
                    <input
                      type="text"
                      placeholder="Enter your name"
                      value={userName}
                      onChange={(e) => setUserName(e.target.value)}
                      className={`w-full px-4 py-3 rounded-lg ${isDark ? 'bg-gray-900 border-gray-700 text-white placeholder-gray-500' : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400'} border focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none`}
                    />
                  </div>

                  <button
                    onClick={joinRoom}
                    disabled={!roomId || !userName}
                    className="w-full py-3 px-4 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-all transform hover:scale-[1.02] active:scale-[0.98] shadow-lg disabled:shadow-none"
                  >
                    Join Room
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`h-screen min-w-screen max-w-screen pt-16 flex flex-col ${isDark ? 'bg-gray-900' : 'bg-gray-50'} transition-colors duration-300`}>
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        <div className={`${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-r lg:border-b-0 border-t lg:border-t-0 w-full lg:w-1/4 flex-shrink-0 transition-colors duration-300 order-2 lg:order-1`}>
          <div className="h-full flex flex-col p-4 space-y-4 overflow-y-auto">
            <div className={`p-4 rounded-xl ${isDark ? 'bg-gray-900/50 border border-gray-700' : 'bg-gray-50 border border-gray-200'}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className={`text-sm font-semibold ${isDark ? 'text-gray-400' : 'text-gray-600'} uppercase tracking-wide`}>Room ID</h3>
                <button
                  onClick={copyRoomId}
                  className={`px-3 py-1 text-xs font-medium rounded-lg transition-all ${isDark ? 'bg-gray-800 hover:bg-gray-700 text-white' : 'bg-gray-200 hover:bg-gray-300 text-white'}`}
                >
                  {copySuccess || 'Copy'}
                </button>
              </div>
              <p className={`text-lg font-mono font-bold ${isDark ? 'text-white' : 'text-gray-900'} break-all`}>{roomId}</p>
            </div>

            {/* Active Users */}
            <div className={`p-4 rounded-xl ${isDark ? 'bg-gray-900/50 border border-gray-700' : 'bg-gray-50 border border-gray-200'} flex-1`}>
              <h3 className={`text-sm font-semibold ${isDark ? 'text-gray-400' : 'text-gray-600'} uppercase tracking-wide mb-3`}>
                Active Users ({users.length})
              </h3>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {users.map((user, index) => (
                  <div key={index} className={`flex items-center space-x-3 p-2 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                      <span className="text-white text-xs font-bold">{user.charAt(0).toUpperCase()}</span>
                    </div>
                    <span className={`text-sm font-medium truncate ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                      {user.slice(0, 12)}...
                    </span>
                  </div>
                ))}
              </div>
              {typing && (
                <div className={`mt-3 text-xs ${isDark ? 'text-blue-400' : 'text-blue-600'} flex items-center space-x-2`}>
                  <div className="flex space-x-1">
                    <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <span>{typing}</span>
                </div>
              )}
            </div>

            {/* Language Selector */}
            <div>
              <label className={`block text-sm font-semibold ${isDark ? 'text-gray-400' : 'text-gray-600'} uppercase tracking-wide mb-2`}>
                Language
              </label>
              <select
                value={language}
                onChange={handleLanguageChange}
                className={`w-full px-4 py-2.5 rounded-lg ${isDark ? 'bg-gray-900 border-gray-700 text-white' : 'bg-gray-50 border-gray-300 text-gray-900'} border focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none`}
              >
                <option value="javascript">JavaScript</option>
                <option value="python">Python</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
                <option value="cpp">MySQL</option>
                <option value="cpp">C#</option>
                <option value="cpp">Ruby</option>
                <option value="cpp">Shell</option>
                <option value="cpp">Kotlin</option>
                <option value="cpp">R</option>
              </select>
            </div>


            <button
              onClick={leaveRoom}
              className="w-full py-2.5 px-4 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg transition-all transform hover:scale-[1.02] active:scale-[0.98]"
            >
              Leave Room
            </button>
          </div>
        </div>

        {/* Editor - Top on mobile, Right on desktop - 75% width */}
        <div className="flex-1 lg:w-3/4 flex flex-col overflow-hidden order-1 lg:order-2">
          {/* Editor Theme Toggle */}
          <div className={`${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-b px-4 py-2 flex items-center justify-between`}>
            <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              Editor Theme
            </span>
            <button
              onClick={toggleEditorTheme}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg transition-all ${isDark ? 'bg-gray-900 hover:bg-gray-700' : 'bg-gray-100 hover:bg-gray-200'}`}
            >
              {editorTheme === "vs-dark" ? (
                <>
                  <svg className="w-4 h-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                  </svg>
                  <span className={`text-xs font-medium ${isDark ? 'text-gray-300' : 'text-gray-300'}`}>Light</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 text-blue-300" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                  <span className={`text-xs font-medium ${isDark ? 'text-gray-300' : 'text-gray-200'}`}>Dark</span>
                </>
              )}
            </button>
          </div>
          
          <div className="flex-1">
            <Editor
              height="100%"
              defaultLanguage={language}
              language={language}
              value={code}
              onChange={handleCodeChange}
              theme={editorTheme}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: "'Fira Code', 'Courier New', monospace",
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 2,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;