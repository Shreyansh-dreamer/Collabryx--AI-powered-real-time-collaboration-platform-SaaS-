import {useState, useEffect} from 'react';
import Navbar from './Navbar.jsx';
import Docs from './Documents/Docs.jsx';
import Editor from './Editor/Editor.jsx';
import GroupChat from './chatSpace/GroupChat.jsx';
import Chatbot from './Chatbot/chatbot.jsx';

function App() {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved && ['light', 'dark', 'system'].includes(saved)) return saved;
    return 'system';
  });

  useEffect(() => {
    const html = document.documentElement;
    if (theme === 'dark') html.classList.add('dark');
    else if (theme === 'light') html.classList.remove('dark');
    else {
      const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      html.classList.toggle('dark', systemDark);
    }

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => {
        const isDark = mediaQuery.matches;
        html.classList.toggle('dark', isDark);
      };
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme]);

  const changeTheme = (newTheme) => {
    setTheme(newTheme);
    if (newTheme === 'system')localStorage.removeItem('theme');
    else localStorage.setItem('theme', newTheme);
  };

  return (
  <>
    <Navbar theme={theme} changeTheme={changeTheme} />
    <Routes>
      <Route path="/" element={<Docs/>}/>
      <Route path="editor" element={<Editor theme={theme}/>}/>
      <Route path="chat" element={<GroupChat/>}/>
      <Route path="chatbot" element={<Chatbot/>}/>
    </Routes>
  </>
);

}

export default App
