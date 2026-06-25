const express = require("express");
const Room = require("../model/RoomModel");
const Message = require("../model/MessageModel");
const {verifyUser} = require("../Middleware/verifyUser.js");
const multer = require("multer");
const cloudinary = require("cloudinary").v2;
const path = require("path");

const router = express.Router();

const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

router.post("/createRoom", verifyUser , async (req, res) => {
  const orga=req.org;
  const room = await Room.create({
    name: req.body.name,
    lastmsg: "",
    org: orga,
    image: req.body.image,
    createdBy: req.user
  });
  res.json(room);
});

router.get("/rooms", verifyUser , async (req, res) => {
  const rooms = await Room.find({ org: req.org }).sort({createdAt: -1});
  res.json(rooms);
});

router.get("/rooms/:roomId", verifyUser , async (req, res) => {
  const messages = await Message.find({ roomId: req.params.roomId }).sort({createdAt: 1});
  res.json(messages);
});

router.post("/rooms/:roomId/message", verifyUser, async (req, res) => {
  const { content } = req.body;
  const { roomId } = req.params;
  if (!content?.trim()) {
    return res.status(400).json({ error: "Empty message" });
  }
  const message = await Message.create({roomId,senderId: req.user,content,});
  await Room.findByIdAndUpdate(roomId, {
    lastmsg: content,
  });
  res.json(message);
});

router.delete("/rooms/:roomId/delete", verifyUser, async (req, res) => {
  try {
    const { roomId } = req.params;
    const userId = req.user;
    const room = await Room.findOne({ _id: roomId, org: req.org });
    if (!room) return res.status(404).json({ message: "Room not found" });
    if (userId.toString() !== room.createdBy.toString()) {
      return res.status(403).json({ message: "Only the owner of the room can delete it" });
    }
    await Room.findByIdAndDelete(roomId);
    const del = await Message.deleteMany({ roomId: roomId, org: req.org });
    console.log(`${del.deletedCount} messages deleted for room ${roomId}`);
    res.json({ message: "Room and its messages deleted successfully" });
  } catch (err) {
    console.error("Error deleting room:", err);
    res.status(500).json({ message: "Internal server error" });
  }
});

router.post("/rooms/:roomId/upload", verifyUser, upload.single("file"), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: "No file uploaded" });
    }

    const uploadToCloudinary = (fileBuffer, fileName) => {
      return new Promise((resolve, reject) => {
        const stream = cloudinary.uploader.upload_stream(
          {
            resource_type: "auto",
            folder: "collabryx_chat",
            public_id: path.parse(fileName).name + "-" + Date.now(),
          },
          (error, result) => {
            if (error) return reject(error);
            resolve(result);
          }
        );
        stream.end(fileBuffer);
      });
    };

    const result = await uploadToCloudinary(req.file.buffer, req.file.originalname);

    res.json({
      fileUrl: result.secure_url,
      fileName: req.file.originalname,
      fileType: req.file.mimetype
    });
  } catch (err) {
    console.error("Cloudinary upload error in route:", err);
    res.status(500).json({ error: "Internal server error during file upload" });
  }
});

module.exports = router;
