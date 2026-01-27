const GoogleStrategy = require('passport-google-oauth20').Strategy;
const mongoose = require('mongoose');
const { UsersModel} = require("../model/UsersModel");
const jwt = require('jsonwebtoken');
const express = require("express");
const passport = require("passport");
const sendOtpMail = require('../utils/sendOtpMail');
const router = express.Router();
const { Signup } = require("../Controllers/AuthController");
const { Login } = require("../Controllers/AuthController");
const { resetPassword } = require("../Controllers/AuthController");
const {signToken} = require('../auth/jwt');
const {verifyToken} = require('../auth/jwt');
const otpStore = new Map();

router.get('/auth/google',
  passport.authenticate('google', { scope:['profile', 'email'] }));

router.get('/auth/google/callback',
  passport.authenticate('google',{failureRedirect:'http://localhost:5173'}),
  async(req,res)=>{
    const user=req.user;
    const payload={id:user._id,org:user.org};
    const token=signToken(payload);
    res.cookie('token',token,{
      httpOnly:true,
      secure:process.env.NODE_ENV==='production',
      sameSite:'lax',
      maxAge:24*60*60*1000,
    });
    res.redirect('http://localhost:5174');
  }
);


router.post('/getOtp', async (req, res) => {
  const { email } = req.body;
  if (!email) return res.status(400).json({ message: 'Email required' });
  const otp = Math.floor(100000 + Math.random() * 900000).toString();
  const expiresAt = Date.now() + 5 * 60 * 1000;
  otpStore.set(email, { otp, expiresAt });
  try {
    await sendOtpMail(email, otp);
    res.status(200).json({ message: 'OTP sent' });
  } catch (err) {
    res.status(500).json({ success: true, message: 'Error sending OTP', error: err.message });
  }
});

router.post('/verifyOTP', async (req, res) => {
  const { email, otp } = req.body;
  const data = otpStore.get(email);
  if (!data || Date.now() > data.expiresAt) {
    return res.status(400).json({ message: 'OTP expired or not found' });
  }
  if (data.otp !== otp) {
    return res.status(401).json({ message: 'Invalid OTP' });
  }
  const tempToken=jwt.sign({email},process.env.DUMMY_SECRET_KEY,{expiresIn:"15m"});
    res.cookie("tempToken", tempToken, {
      httpOnly: true,
      maxAge: 15 * 60 * 1000,
      secure: false,
      sameSite: "Lax", 
    });
  const user = await UsersModel.findOne({ email });
  if (user) {
    return res.status(200).json({ status: 'login' });
  } else {
    return res.status(200).json({ status: 'signup' });
  }
});

router.post("/signup", Signup);
router.post('/login', Login);
router.post("/resetPassword", resetPassword);

module.exports = router;