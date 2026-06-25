const {verifyToken} = require('../auth/jwt');
const Message = require('../model/MessageModel');
const Room = require('../model/RoomModel');

module.exports = (io) => {

  io.use((socket, next) => {
    const cookie = socket.handshake.headers?.cookie;
    const token =socket.handshake.auth?.token || cookie?.split("; ").find(c => c.startsWith("token="))?.split("=")[1];
    if(!token) return next(new Error("Auth token missing"));
    const decoded = verifyToken(token);
    if(!decoded) return next(new Error("Invalid token"));
    socket.userId = decoded.id;
    socket.org = decoded.org;
    next();
  });

  io.on("connection", (socket) => {

    socket.emit("auth-info", {
      userId: socket.userId,
      org: socket.org,
    });

    socket.on("join-room", async (roomId) => {
      try {
        const room = await Room.findById(roomId);
        if (!room) return;
        if (room.org !== socket.org) return;
        socket.join(roomId);
      } catch (err) {
        console.error("Join room error:", err.message);
      }
    });

    socket.on("leaveRoom", (roomId) => {
      socket.leave(roomId);
    });

    socket.on("send-message", async ({roomId, content, fileUrl, fileName, fileType}) => {
      const room = await Room.findById(roomId);
      if(!room) return;
      if(room.org !== socket.org) return;
      const message = await Message.create({
        roomId,
        senderId: socket.userId,
        content,
        fileUrl,
        fileName,
        fileType
      });
      const lastmsg = fileUrl ? `📎 File: ${fileName}` : content;
      await Room.findByIdAndUpdate(roomId,{ lastmsg, updatedAt: new Date() });
      io.to(roomId).emit("new-message",{
        id: message._id,
        senderId: socket.userId,
        content,
        fileUrl,
        fileName,
        fileType,
        createdAt: message.createdAt,
      });
    });

    socket.on("disconnect", () => {});
  });
};
