import { motion } from "motion/react";
import { useNavigate } from "react-router-dom";

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="w-full min-w-screen h-screen bg-gradient-to-b from-black via-gray-900 to-black text-white flex flex-col items-center justify-center relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-full z-0">
        <div className="absolute w-100 h-100 bg-cyan-500 rounded-full opacity-30 filter blur-3xl animate-pulse left-1/3 top-10"></div>
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="z-10 text-center p-4"
      >
        <h1 className="text-6xl font-extrabold mb-4">404</h1>
        <p className="text-2xl mb-6">Lost in <span className="font-extrabold">Collabryx</span></p>
        <p className="mb-8 text-gray-400 max-w-md mx-auto">
          The page you're looking for doesn't exist.
        </p>
        <div className="flex justify-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="bg-black hover:bg-black-700 hover:border hover:border-white px-6 py-2 cursor-pointer rounded-lg text-white font-semibold shadow-lg"
          >
            🏠 Beam me back Home
          </button>
        </div>
      </motion.div>

      <motion.img
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.8 }}
        src="https://cdn-icons-png.flaticon.com/512/3214/3214425.png"
        alt="Astronaut"
        className="w-28 h-28 mt-12 z-10 animate-float"
      />
    </div>
  );
};

export default NotFound;