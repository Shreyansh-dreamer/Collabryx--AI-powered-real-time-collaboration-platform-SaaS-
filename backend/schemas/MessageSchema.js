const { Schema } = require("mongoose");
const mongoose = require("mongoose");

const MessageSchema = mongoose.Schema({
    roomId: { type: mongoose.Schema.Types.ObjectId, required: true },
    senderId: { type: mongoose.Schema.Types.ObjectId, required: true },
    content: { type: String, required: false },
    fileUrl: { type: String },
    fileName: { type: String },
    fileType: { type: String }
}, { timestamps: true });

module.exports =  MessageSchema ;
