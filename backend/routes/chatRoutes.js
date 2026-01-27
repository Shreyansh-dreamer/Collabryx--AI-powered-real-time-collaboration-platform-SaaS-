const express = require("express");
const Room = require("../model/RoomModel");
const Message = require("../model/MessageModel");
const {verifyUser} = require("../Middleware/verifyUser.js");

const router = express.Router();

router.post("/createRoom", verifyUser , async (req, res) => {
  const orga=req.org;
  const room = await Room.create({
    name: req.body.name,
    lastmsg: "",
    org: orga,
    image: req.body.image,
    createdBy: req.user._id
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
  const message = await Message.create({roomId,senderId: req.userId,content,});
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

module.exports = router;
