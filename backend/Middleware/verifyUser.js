const jwt = require("jsonwebtoken");
const { verifyToken } = require('../auth/jwt');

const verifyUser = (req, res, next) => {
  const token = req.cookies.token;
  if (!token) return res.status(401).json({ message: "Auth token not found" });
  try {
    const decoded = verifyToken(token);
    if(!decoded) return res.status(401).json({ message: "Invalid token" });
    req.user = decoded.id; 
    req.org = decoded.org;
    console.log(" Decoded ID:", req.user);
    console.log(" Decoded org:", req.org);
    next();
  } catch (err) {
    console.log(" Invalid token");
    return res.status(401).json({ message: "Invalid token" });
  }
};

module.exports = {verifyUser};