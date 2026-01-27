const nodemailer = require('nodemailer');

const transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: process.env.Email,
    pass: process.env.app_pass,
  },
});

const sendOtpMail = async (email, otp) => {
  const mailOptions = {
    from: "freeapiuse@gmail.com",
    to: email,
    subject: "Your OTP Code",
    html: `<p><h1>Do Not Reply</h1>Your OTP is <b>${otp}</b>. It is valid for 5 minutes.</p>`
  };

try {
    const info = await transporter.sendMail(mailOptions);
    console.log(" Mail sent:", info.response);
  } catch (err) {
    console.error(" Failed to send mail:", err);
    throw err;
  }
};

module.exports = sendOtpMail;