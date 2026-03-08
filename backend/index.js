require("dotenv").config();
require("./config/passport");

const express = require("express");
const mongoose = require("mongoose");
const bodyParser = require("body-parser");
const cors = require("cors");
const passport = require("passport");
const cookieParser = require("cookie-parser");
const session = require("express-session");
const http = require("http");
const { Server } = require("socket.io");

// const { connectRedis } = require("./redisClient");

const authRoutes = require("./routes/authRoutes");
const userSpecificRoutes = require("./routes/userSpecificRotes");
const chatRoutes = require("./routes/chatRoutes");
const socketHandler = require("./socketIndex");

const PORT = process.env.PORT || 3000;
const url = process.env.MONGO_URL || "mongodb://localhost:27017/mydb";

const app = express();

app.use(bodyParser.json());
app.use(cookieParser());

app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
    maxAge: 24 * 60 * 60 * 1000,
  },
}));

app.use(passport.initialize());
app.use(passport.session());

const allowedOrigins = [
  "http://localhost:5173",
  "http://localhost:5174",
  "http://localhost:3000",
  "http://localhost:8000",
  "http://localhost:8501"
];

app.use(cors({
  origin: (origin, cb) => {
    if (!origin || allowedOrigins.includes(origin)) cb(null, true);
    else cb(new Error("Not allowed by CORS"));
  },
  credentials: true,
}));

app.use("/", authRoutes);
app.use("/", userSpecificRoutes);
app.use("/", chatRoutes);

const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: allowedOrigins,
    credentials: true
  }
});

socketHandler(io);

(async function startServer() {
  try {
    await mongoose.connect(url);
    console.log("Database connected");

    // await connectRedis();
    // console.log("Redis connected")

    server.listen(PORT, "0.0.0.0", () => {
      console.log(`Backend running on http://localhost:${PORT}`);
    });
  } catch (err) {
    console.error("Startup failed:", err);
  }
})();
