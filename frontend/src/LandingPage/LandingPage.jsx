import React from 'react';
import Footer from './Footer.jsx';
import Navbar from './Navbar.jsx';
import Page from './Page.jsx';
import LoginModal from './LoginModal';
import SignupModal from './SignupModal';
import { useState,useEffect,useRef } from 'react';

const LandingPage = () => {
  const [showLogin, setShowLogin] = useState(false);
  const [showLoginVerified, setShowLoginVerified] = useState(false);
  const [showSignup, setShowSignup] = useState(false);
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved && ['light', 'dark', 'system'].includes(saved)) return saved;
    return 'system';
  });

  const footerRef=useRef(null);

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
    if (newTheme === 'system') localStorage.removeItem('theme');
    else localStorage.setItem('theme', newTheme);
  };

  const scrollToFooter=()=>{
    footerRef.current?.scrollIntoView({behaavior:"smooth"});
  }

  return (
    <div>
      <Navbar
        theme={theme}
        changeTheme={changeTheme}
        onContactClick={scrollToFooter}
        onLoginClick={() => setShowLogin(true)}
        onSignupClick={() => setShowSignup(true)}
      />
      <Page/>
      {showLogin && !showLoginVerified && (
        <LoginModal
          onClose={() => setShowLogin(false)}
          onOtpVerified={() => {
            setShowLogin(false);
            setShowLoginVerified(true);
          }}
        />
      )}
      {showLoginVerified && (
        <LoginFlowModal onClose={() => setShowLoginVerified(false)} />
      )}
      {showSignup && <SignupModal onClose={() => setShowSignup(false)} />}
      <Footer ref={footerRef}/>
    </div>
  )
}

export default LandingPage