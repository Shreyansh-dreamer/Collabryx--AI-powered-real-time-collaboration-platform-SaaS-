import { useState,useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";

function SignupModal({ onClose }) {
  const [email, setEmail] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpVerified, setOtpVerified] = useState(false);
  const [username, setUsername] = useState("");
  const [org, setOrg] = useState("");
  const [password, setPassword] = useState("");
  const [resendTimer, setResendTimer] = useState(30);
  const [canResend, setCanResend] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [otpResendTrigger, setOtpResendTrigger] = useState(0);

  const validatePassword = (pwd) => {
    const regex = /^(?=.*[a-zA-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return regex.test(pwd);
  };

  const handleSendOtp = async () => {
    try {
      const res = await axios.post("http://localhost:3000/getOtp", { email }, { withCredentials: true });
      if (res.status == 200) {
        setOtpSent(true);
        setCanResend(false);
        setOtpResendTrigger((prev) => prev + 1);
      }
    } catch (err) {
      console.error("Failed to send OTP", err);
    }
  };

  const handleVerifyOtp = async () => {
    try {
      const res = await axios.post("http://localhost:3000/verifyOtp", { email, otp }, { withCredentials: true });
      if (res.status == 200) {
        setOtpVerified(true);
      }
    } catch (err) {
      console.error("OTP verification failed", err);
    }
  };


  const handleRegister = async () => {
    if (!validatePassword(password)) {
      setPasswordError("Password must be at least 8 characters long and include letters, numbers, and a special character.");
      return;
    }
    setPasswordError("");
    try {
      const res = await axios.post(
        "http://localhost:3000/signup", { username, password, org }, { withCredentials: true }
      );
      console.log("Registered:", res.data);
      window.location.href = "http://localhost:5174"; 
      }
    catch (err) {
      console.error("Registration failed", err);
    }
  };

  // ⏱ Resend timer logic
  useEffect(() => {
    let timer;
    if (otpSent && !otpVerified) {
      setCanResend(false);
      setResendTimer(30);
      timer = setInterval(() => {
        setResendTimer((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            setCanResend(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [otpSent,otpResendTrigger]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      ></div>
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="relative bg-white dark:bg-white rounded-lg shadow-lg px-8 py-6 w-[90%] max-w-sm z-10"
      >
        <h2 className="text-center text-xl text-black font-bold mb-4">Sign Up</h2>
        <input
          type="email"
          placeholder="Email"
          value={email}
          disabled={otpSent || otpVerified}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 text-black rounded mb-4 focus:outline-none focus:ring focus:border-blue-400"
        />
        {!otpSent && (
          <button
            onClick={handleSendOtp}
            className="w-full !bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded mb-4"
          >
            Send OTP
          </button>
        )}


        {otpSent && !otpVerified && (
          <>
            <input
              type="text"
              placeholder="Enter OTP"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 text-black rounded mb-4 focus:outline-none focus:ring focus:border-blue-400"
            />

            <button
              onClick={handleVerifyOtp}
              className="w-full !bg-green-600 hover:!bg-green-700 text-white font-semibold py-2 rounded mb-4"
            >
              Verify OTP
            </button>
          </>
        )}


        {otpSent && !otpVerified && (
          <>
            {canResend ? (
              <button
                onClick={handleSendOtp}
                className="w-full !bg-yellow-500 hover:!bg-yellow-600 text-white font-semibold py-2 rounded mb-4"
              >
                Resend OTP
              </button>
            ) : (
              <p className="text-center text-sm text-gray-500 mb-4">
                You can resend OTP in {resendTimer}s
              </p>
            )}
          </>
        )}



        {otpVerified && (
          <>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 text-black rounded mb-4 focus:outline-none focus:ring focus:border-blue-400"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 text-black rounded mb-4 focus:outline-none focus:ring focus:border-blue-400"
            />
            <input
              type="text"
              placeholder="Organisation"
              value={org}
              onChange={(e) => setOrg(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 text-black rounded mb-4 focus:outline-none focus:ring focus:border-blue-400"
            />
            {passwordError && (
              <p className="text-red-600 text-sm mb-2">{passwordError}</p>
            )}
            <button
              onClick={handleRegister}
              className="w-full !bg-blue-600 hover:!bg-blue-700 text-white font-semibold py-2 rounded mb-4"
            >
              Register
            </button>
          </>
        )}
      </motion.div>
    </div>
  );
}

export default SignupModal;