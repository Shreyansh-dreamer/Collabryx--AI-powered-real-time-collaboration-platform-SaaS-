const {Schema}=require("mongoose");
const mongoose = require('mongoose');
const { Types } = mongoose;

const RoomSchema = mongoose.Schema({
    name: String,
    lastmsg: String,
    org: String,
    image: String,
    createdBy: mongoose.Schema.Types.ObjectId
}, { timestamps: true });

module.exports=RoomSchema;