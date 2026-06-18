import { useEffect, useState } from "react";
import axios from "axios";
import { useTheme } from "../ThemeContext.jsx";

const Chatbot = () => {
  const [userParams, setUserParams] = useState(null); 
  const { isDark } = useTheme();


  useEffect(() => {
    const init = async () => {
      try {
        const res = await axios.get("http://localhost:3000/whoAmI", { withCredentials: true });
        setUserParams({ email: res.data.email, org: res.data.org });
      } catch (err) {
        window.location.href = "/login";
      }
    };
    init();
  }, []);


  const streamlitUrl = userParams
    ? `http://localhost:8501?${new URLSearchParams({ ...userParams, theme: isDark ? "dark" : "light" }).toString()}`
    : null;

  if (!streamlitUrl) {
    return (
      <div
        className={`flex items-center justify-center transition-colors duration-200 ${
          isDark ? "bg-gray-900" : "bg-gray-50"
        }`}
        style={{ width: "100vw", height: "100vh", paddingTop: "64px" }}
      >
        <div className="flex flex-col items-center gap-4">
          <div
            className={`w-12 h-12 rounded-full border-4 border-t-transparent animate-spin ${
              isDark ? "border-blue-400" : "border-blue-500"
            }`}
          />
          <p className={`text-sm font-medium ${isDark ? "text-gray-400" : "text-gray-500"}`}>
            Loading AI Assistant...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`transition-colors duration-200 ${isDark ? "bg-gray-900" : "bg-gray-50"}`}
      style={{ width: "100vw", height: "100vh", overflow: "hidden", paddingTop: "64px" }}
    >
      <iframe
        key={streamlitUrl}
        src={streamlitUrl}
        style={{ width: "100%", height: "100%", border: "none" }}
        allow="clipboard-read; clipboard-write"
      />
    </div>
  );
};

export default Chatbot;