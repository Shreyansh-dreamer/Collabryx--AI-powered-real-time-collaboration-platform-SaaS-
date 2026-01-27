const {model}=require("mongoose");

const MessageSchema=require('../schemas/MessageSchema');

const Message = model("Message", MessageSchema);

module.exports =  Message ;