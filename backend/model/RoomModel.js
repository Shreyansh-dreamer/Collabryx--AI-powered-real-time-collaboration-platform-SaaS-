const mongoose = require("mongoose");
const RoomSchema = require("../schemas/RoomSchema");

const Room = mongoose.model("Room", RoomSchema);

module.exports = Room;
