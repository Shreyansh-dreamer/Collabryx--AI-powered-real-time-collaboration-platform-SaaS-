import { Routes, Route } from "react-router-dom";
import { ThemeProvider } from './ThemeContext.jsx';
import Navbar from './Navbar.jsx';
import Docs from './Documents/Docs.jsx';
import Editor from './Editor/Editor.jsx';
import GroupChat from './chatSpace/GroupChat.jsx';
import Chatbot from './Chatbot/Chatbot.jsx';

function App() {
  return (
    <ThemeProvider>
      <Navbar />
      <Routes>
        <Route path="/" element={<Docs />} />
        <Route path="editor" element={<Editor />} />
        <Route path="chat" element={<GroupChat />} />
        <Route path="chatbot" element={<Chatbot />} />
      </Routes>
    </ThemeProvider>
  );
}

export default App;
