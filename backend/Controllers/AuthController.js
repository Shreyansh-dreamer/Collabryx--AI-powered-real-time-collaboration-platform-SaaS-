const { UsersModel: User } = require("../model/UsersModel");
const bcrypt = require("bcrypt");
const jwt = require('jsonwebtoken');
const {signToken} = require('../auth/jwt');
const {verifyToken} = require('../auth/jwt');

function isPasswordStrong(password) {
  const regex = /^(?=.*[a-zA-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
  return regex.test(password);
}

module.exports.Signup = async (req, res, next) => {
  const token = req.cookies.tempToken;
  if(!token) return res.redirect("http://localhost:5173")
  const payload=jwt.verify(token,process.env.DUMMY_SECRET_KEY);
  const {email}=payload;
  try {
    const {username,password,org} = req.body;
    if (!isPasswordStrong(password)) {
      return res.status(400).json({
        message:
          "Password must be at least 8 characters long and include letters, numbers, and a special character.",
      });
    }
    const hashedPassword = await bcrypt.hash(password, 10);
    const user = await User.create({ email, username, password : hashedPassword,org:org});
    const token = signToken({ id: user._id, org: user.org });
    res.cookie("token", token, {
      httpOnly: true,
      secure: false,
      sameSite: "Lax", 
    });
    res.status(201).json({ message: "User signed in successfully", success: true, user,status: 'yes' });
    next();
  } catch (error) {
    console.error(error);
  }
};

module.exports.Login = async (req, res, next)=>{
  try {
    const {email,password } = req.body;
    if(!email || !password ){
      return res.json({message:'All fields are required'})
    }
    const user = await User.findOne({ email });
    const auth = await bcrypt.compare(password,user.password)
    if (!auth) {
      return res.status(401).json({ message: "Invalid email or password" }); 
    }
    const token = signToken({ id: user._id, org: user.org });
    res.cookie("token", token, {
      httpOnly: true,
      secure: false,
      sameSite: "Lax",
    });
    res.clearCookie("tempToken", {
    httpOnly: true,
    secure: false,
    sameSite: "Lax",
  });
    res.status(201).json({ message: "User logged in successfully", success: true,status: 'yes' });
    next()
  } catch (error) {
    console.error(error);
  }
}

module.exports.resetPassword = async (req, res) => {
  const token = req.cookies.tempToken;
  if(!token) return res.redirect("http://localhost:5173")
  const payload=jwt.verify(token,process.env.DUMMY_SECRET_KEY);
  const {email}=payload;
  try {
    const { newPassword } = req.body;
    if (!email || !newPassword) {
      return res.status(400).json({ message: "Email and new password are required." });
    }
    if (!isPasswordStrong(newPassword)) {
      return res.status(400).json({
        message:
          "Password must be at least 8 characters long and include letters, numbers, and a special character.",
      });
    }
    const hashedPassword = await bcrypt.hash(newPassword, 10);
    const user = await User.findOneAndUpdate(
      { email },
      { $set: { password: hashedPassword } },
      { new: true }
    );
    if (!user) {
      return res.status(404).json({ message: "User not found." });
    }
    const token = signToken({ id: user._id, org: user.org });
    res.cookie("token", token, {
      httpOnly: true,
      secure: false,
      sameSite: "Lax",
    });
    res.clearCookie("tempToken", {
    httpOnly: true,
    secure: false,
    sameSite: "Lax",
  });
    res.status(200).json({ message: "Password updated successfully." });
  } catch (error) {
    console.error("Error resetting password:", error);
    res.status(500).json({ message: "Internal server error." });
  }
};
