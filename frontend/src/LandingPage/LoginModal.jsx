import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";

function LoginModal({ onClose }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [forgotMode, setForgotMode] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpVerified, setOtpVerified] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [resendTimer, setResendTimer] = useState(30);
  const [canResend, setCanResend] = useState(false);
  const [otpResendTrigger, setOtpResendTrigger] = useState(0);

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
  }, [otpSent, otpResendTrigger]);

  const validatePassword = (pwd) => {
    const regex = /^(?=.*[a-zA-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return regex.test(pwd);
  };

  const handleLogin = async () => {
    if (!email || !password) {
      return setStatusMsg("Email and password are required.");
    }
    try {
      const res = await axios.post("http://localhost:3000/login", { email, password }, { withCredentials: true });
      if (res.status === 201) {
        setStatusMsg("Login successful!");
        window.location.href = "http://localhost:5174";
      }
    } catch (err) {
      setStatusMsg("Login failed: " + (err.response?.data?.message || "Unknown error"));
    }
  };

  const handleSendOtp = async () => {
    if (!email) {
      setStatusMsg("Please enter your email.");
      return;
    }

    try {
      const res = await axios.post("http://localhost:3000/getOtp", { email }, { withCredentials: true });
      console.log("Sending OTP to", email, otp);
      if (res.status === 200) {
        setOtp("");
        setOtpVerified(false);
        setOtpSent(true);
        setCanResend(false);
        setOtpResendTrigger((prev) => prev + 1);
        setStatusMsg("OTP sent to your email.");
      }
    } catch (err) {
      setStatusMsg(err.response?.data?.message || "Failed to send OTP.");
    }
  };

  const handleVerifyOtp = async () => {
    try {
      const res = await axios.post("http://localhost:3000/verifyOtp", { email, otp }, { withCredentials: true });
      if (res.status === 200) {
        setOtpVerified(true);
        setStatusMsg("OTP verified. Set your new password.");
      }
    } catch (err) {
      setStatusMsg(err.response?.data?.message || "Invalid OTP.");
    }
  };

  const handleResetPassword = async () => {
    if (!validatePassword(newPassword)) {
      setPasswordError("Password must be at least 8 characters long and include letters, numbers, and a special character.");
      return;
    }
    try {
      const res = await axios.post("http://localhost:3000/resetPassword", { email, newPassword }, { withCredentials: true });
      if (res.status === 200) {
        setStatusMsg("Password reset successful.");
        setForgotMode(false);
        setOtpSent(false);
        setOtpVerified(false);
        setOtp("");
        setNewPassword("");
        window.location.href = "http://localhost:5174";
      }
    } catch (err) {
      setStatusMsg("Failed to reset password.");
    }
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
    >
      <motion.div
        onClick={(e) => e.stopPropagation()}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="relative bg-white rounded-lg shadow-lg px-8 py-6 w-[90%] max-w-sm z-10"
      >
        <h2 className="text-center text-xl font-bold text-black mb-4">
          {forgotMode ? "Reset Password" : "Sign In"}
        </h2>

        {/* Email */}
        <input
          type="email"
          placeholder="Email"
          value={email}
          disabled={otpVerified}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-4 py-2 mb-3 border border-gray-300 text-black rounded focus:outline-none focus:ring"
        />

        {/* Normal login */}
        {!forgotMode && (
          <>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 mb-3 border border-gray-300 text-black rounded focus:outline-none focus:ring"
            />
            <button
              onClick={handleLogin}
              className="w-full !bg-blue-600 hover:!bg-blue-700 text-white font-semibold py-2 rounded"
            >
              Login
            </button>

            <p
              className="text-sm mt-3 text-blue-600 text-center cursor-pointer hover:underline"
              onClick={() => {
                if (!email) return setStatusMsg("Please enter your email first.");
                setForgotMode(true);
                setOtp("");
                setOtpSent(false);
                setOtpVerified(false);
                setNewPassword("");
                setPasswordError("");
                setStatusMsg("");
                setCanResend(false);
                setOtpResendTrigger((prev) => prev + 1);
              }}
            >
              Forgot password?
            </p>
          </>
        )}

        {/* Forgot password flow */}
        {forgotMode && !otpSent && !otpVerified && (
          <button
            onClick={handleSendOtp}
            className="w-full !bg-blue-600 hover:!bg-blue-700 text-white font-semibold py-2 rounded"
          >
            Send OTP
          </button>
        )}

        {forgotMode && otpSent && !otpVerified && (
          <>
            <input
              type="text"
              placeholder="Enter OTP"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              className="w-full px-4 py-2 mb-3 border border-gray-300 text-black rounded focus:outline-none focus:ring"
            />
            <button
              onClick={handleVerifyOtp}
              className="w-full !bg-green-600 hover:!bg-green-700 text-white font-semibold py-2 rounded mb-3"
            >
              Verify OTP
            </button>

            {canResend ? (
              <button
                onClick={handleSendOtp}
                className="w-full !bg-yellow-500 !hover:bg-yellow-600 text-white font-semibold py-2 rounded mb-3"
              >
                Resend OTP
              </button>
            ) : (
              <p className="text-center text-sm text-gray-500 mb-3">
                You can resend OTP in {resendTimer}s
              </p>
            )}
          </>
        )}

        {forgotMode && otpVerified && (
          <>
            <input
              type="password"
              placeholder="New Password"
              value={newPassword}
              onChange={(e) => {
                setNewPassword(e.target.value);
                setPasswordError("");
              }}
              className="w-full px-4 py-2 mb-2 border border-gray-300 text-black rounded focus:outline-none focus:ring"
            />
            {passwordError && (
              <p className="text-sm text-red-600 mb-2">{passwordError}</p>
            )}
            <button
              onClick={handleResetPassword}
              className="w-full !bg-yellow-600 hover:!bg-yellow-700 text-white font-semibold py-2 rounded"
            >
              Reset Password
            </button>
          </>
        )}

        {forgotMode && (
          <p
            className="text-sm mt-3 text-blue-600 text-center cursor-pointer hover:underline"
            onClick={() => {
              setForgotMode(false);
              setOtp("");
              setOtpSent(false);
              setOtpVerified(false);
              setNewPassword("");
              setStatusMsg("");
            }}
          >
            Back to Login
          </p>
        )}

        {statusMsg && (
          <p className="mt-4 text-center text-sm text-blue-700">{statusMsg}</p>
        )}

        <div className="text-center my-3 text-sm text-gray-500">or sign in with</div>

        {/* Google Login */}
        <div className="flex justify-center">
          <button
            onClick={() => (window.location.href = "http://localhost:3000/auth/google")}
            className="flex items-center gap-2 !bg-white px-4 py-1 border border-gray-300 rounded shadow-sm hover:shadow-md"
          >
            <img
              src="https://www.svgrepo.com/show/475656/google-color.svg"
              className="w-5 h-5"
              alt="Google"
            />
            <span className="text-black font-medium">Google</span>
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export default LoginModal;