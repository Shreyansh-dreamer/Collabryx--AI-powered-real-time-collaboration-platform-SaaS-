module.exports = (io) => {
  require("./sockets/chat.socket")(io);
  require("./sockets/editor.socket")(io);
};
