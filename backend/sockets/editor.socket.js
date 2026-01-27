const { verifyToken } = require("../auth/jwt");

module.exports = (io) => {

  io.use((socket, next) => {
    const cookie = socket.handshake.headers?.cookie;
    const token = socket.handshake.auth?.token || cookie?.split("; ").find(c => c.startsWith("token="))?.split("=")[1];
    if (!token) return next(new Error("Auth token missing"));
    const decoded = verifyToken(token);
    if (!decoded) return next(new Error("Invalid token"));
    socket.userId = decoded.id;
    next();
  });

  const rooms = new Map();

  io.on("connection", (socket) => {

    let currentRoom = null;
    let currentUser = null;

  
    socket.on("join", ({ roomId, userName }) => {
        if (currentRoom) {
        socket.leave(currentRoom);
        rooms.get(currentRoom).delete(currentUser);
        io.to(currentRoom).emit("userJoined", Array.from(rooms.get(currentRoom)));
        }

        currentRoom = roomId;
        currentUser = userName;

        socket.join(roomId);
        if (!rooms.has(roomId)) {
        rooms.set(roomId, new Set());
        }
        rooms.get(roomId).add(userName);
        io.to(roomId).emit("userJoined", Array.from(rooms.get(currentRoom)));
    });



    socket.on("codeChange", ({ roomId, code }) => {
        socket.to(roomId).emit("codeUpdate", code);
    });


    socket.on("leaveRoom", () => {
        if (currentRoom && currentUser) {
            rooms.get(currentRoom).delete(currentUser);
            io.to(currentRoom).emit("userJoined", Array.from(rooms.get(currentRoom)));
            socket.leave(currentRoom);
            currentRoom = null;
            currentUser = null;
        }
    });


    socket.on("typing", ({ roomId, userName }) => {
        socket.to(roomId).emit("userTyping", userName);
    });


    socket.on("languageChange", ({ roomId, language }) => {
        io.to(roomId).emit("languageUpdate", language);
    });

    
    socket.on("disconnect", () => {
        if (currentRoom && currentUser) {
        rooms.get(currentRoom).delete(currentUser);
        io.to(currentRoom).emit("userJoined", Array.from(rooms.get(currentRoom)));
        }
        console.log("user Disconnected");
    });
   });
};
