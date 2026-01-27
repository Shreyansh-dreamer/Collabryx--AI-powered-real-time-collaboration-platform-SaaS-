const {model}=require("mongoose");

const {UsersSchema}=require('../schemas/UsersSchema');

const UsersModel = model("User", UsersSchema);

module.exports = { UsersModel };