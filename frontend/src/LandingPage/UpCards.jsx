import { motion } from "framer-motion";

function UpCards({ icon, bgColor, title, description }) {
  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      drag
      dragConstraints={{ top: 0, bottom: 0, left: 0, right: 0 }} 
      dragElastic={0.2} 
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="w-52 rounded-xl shadow-md px-4 py-5 h-52 cursor-grab active:cursor-grabbing"
      style={{ backgroundColor: bgColor }}
    >
      {/* Icon box */}
      <div className="w-9 h-9 bg-white rounded-md flex items-center justify-center mb-4">
        {icon}
      </div>

      {/* Title */}
      <h3 className="font-semibold text-gray-900 text-lg leading-snug mb-1">
        {Array.isArray(title) ? (
          <>
            {title[0]} <br /> {title[1]}
          </>
        ) : (
          title
        )}
      </h3>

      {/* Description */}
      <p className="text-sm text-black/70 leading-snug">
        {description}
      </p>
    </motion.div>
  );
}

export default UpCards;