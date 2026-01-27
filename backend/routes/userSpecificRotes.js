const express = require("express");
const router = express.Router();
const { verifyUser } = require("../Middleware/verifyUser");
const { redisClient } = require("../redisClient");
const { UsersModel: User } = require("../model/UsersModel");

router.get("/whoAmI", verifyUser, async (req, res) => {
  try {
    const userId = req.user;
    const cacheKey = `whoAmI:${userId}`;
    const ttl = 15 * 60;
    const cached = await redisClient.get(cacheKey);
    if (cached) {
      return res.json(JSON.parse(cached));
    }
    const user = await User.findById(userId).select("username name email org photos");
    if (!user) return res.status(404).json({ message: "User not found" });
    const userData = {
      username: user.username || user.name,
      email: user.email,
      org: user.org,
      photos: user.photos,
    };
    await redisClient.setEx(cacheKey, ttl, JSON.stringify(userData));
    res.json(userData);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: "Internal server error" });
  }
});


router.post("/logout",verifyUser, (req, res) => {
    try {
        res.clearCookie("token", {
            httpOnly: true,
            secure: false,
            sameSite: "Lax",
        });
        res.status(200).json({ message: 'Logged out', status: 'logout' });
    } catch (err) {
        res.status(500).json({ message: "Logout failed", error: err.message });
    }
});

module.exports = router;