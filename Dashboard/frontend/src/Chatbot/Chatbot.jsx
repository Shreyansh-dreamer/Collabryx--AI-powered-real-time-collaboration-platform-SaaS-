import { useEffect, useRef, useState } from "react";
import axios from "axios";

const STREAMLIT_BASE = "http://localhost:8501";

const Chatbot = () => {
  const containerRef = useRef(null);
  const [iframeHeight, setIframeHeight] = useState("100%");
  const [streamlitUrl, setStreamlitUrl] = useState(null);
  const [authError, setAuthError] = useState(false);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await axios.get("http://localhost:3000/whoAmI", {
          withCredentials: true,
        });
        if (res.data?.email && res.data?.org) {
          const params = new URLSearchParams({
            email: res.data.email,
            org:   res.data.org,
          });
          setStreamlitUrl(STREAMLIT_BASE + "?" + params.toString());
        } else {
          setAuthError(true);
        }
      } catch (err) {
        const cachedEmail = localStorage.getItem("userEmail");
        const cachedOrg   = localStorage.getItem("userOrg");
        if (cachedEmail && cachedOrg) {
          const params = new URLSearchParams({ email: cachedEmail, org: cachedOrg });
          setStreamlitUrl(STREAMLIT_BASE + "?" + params.toString());
        } else {
          setAuthError(true);
        }
      }
    };
    fetchUser();
  }, []);

  useEffect(() => {
    const calcHeight = () => {
      if (containerRef.current) {
        const top = containerRef.current.getBoundingClientRect().top;
        setIframeHeight(window.innerHeight - top + "px");
      }
    };
    calcHeight();
    window.addEventListener("resize", calcHeight);
    return () => window.removeEventListener("resize", calcHeight);
  }, []);

  if (authError) {
    return (
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        height: iframeHeight, background: "#f8fafc",
      }}>
        <div style={{
          textAlign: "center", padding: 40, borderRadius: 16,
          background: "#fff", boxShadow: "0 4px 24px rgba(0,0,0,.1)",
        }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>&#128274;</div>
          <h2 style={{ margin: "0 0 8px", fontSize: 20 }}>Not Authenticated</h2>
          <p style={{ color: "#64748b", marginBottom: 24 }}>Please log in to use the chatbot</p>
          <a href="/login" style={{
            padding: "10px 24px", borderRadius: 10, background: "#2563eb",
            color: "#fff", textDecoration: "none", fontWeight: 700,
          }}>Go to Login</a>
        </div>
      </div>
    );
  }

  if (!streamlitUrl) {
    return (
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        height: iframeHeight, background: "#f8fafc",
      }}>
        <div style={{ textAlign: "center" }}>
          <div style={{
            width: 48, height: 48, borderRadius: "50%",
            border: "4px solid #e2e8f0", borderTopColor: "#3b82f6",
            animation: "spin 0.8s linear infinite", margin: "0 auto 16px",
          }} />
          <p style={{ color: "#64748b" }}>Loading chatbot...</p>
        </div>
        <style>{"@keyframes spin { to { transform: rotate(360deg); } }"}</style>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: iframeHeight, overflow: "hidden", margin: 0, padding: 0 }}
    >
      <iframe
        src={streamlitUrl}
        title="Multi Utility Chatbot"
        style={{ width: "100%", height: "100%", border: "none", display: "block" }}
        allow="clipboard-read; clipboard-write"
      />
    </div>
  );
};

export default Chatbot;