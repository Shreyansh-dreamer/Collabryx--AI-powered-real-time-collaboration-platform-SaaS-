const passport = require("passport");
const GoogleStrategy = require("passport-google-oauth20").Strategy;
const { UsersModel: User } = require("../model/UsersModel");

passport.use(
  new GoogleStrategy(
    {
      clientID: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      callbackURL: process.env.GOOGLE_CALLBACK_URL,
    },
    async (accessToken, refreshToken, profile, done) => {
      try {
        console.log("Google profile:", profile);

        // Check if user with googleId already exists
        let user = await User.findOne({ googleId: profile.id });
        if (user) return done(null, user);

        const email = profile.emails?.[0]?.value || '';

        // Check if user with same email already exists
        let existingUser = await User.findOne({ email });

        if (existingUser) {
          existingUser.googleId = profile.id;
          existingUser.name = existingUser.name || profile.displayName;
          existingUser.photos = existingUser.photos || profile.photos?.[0]?.value || '';
          await existingUser.save();
          return done(null, existingUser);
        }

        // If not found by googleId or email, create a new user
        const newUser = new User({
          googleId: profile.id,
          name: profile.displayName,
          photos: profile.photos?.[0]?.value || '',
          email,
        });

        await newUser.save();
        return done(null, newUser);
      } catch (err) {
        console.error("Google strategy error:", err);
        return done(err, null);
      }
    }
  )
);

passport.serializeUser((user, done) => {
  done(null, user.id);
});

passport.deserializeUser(async (id, done) => {
  const user = await User.findById(id);
  done(null, user);
});