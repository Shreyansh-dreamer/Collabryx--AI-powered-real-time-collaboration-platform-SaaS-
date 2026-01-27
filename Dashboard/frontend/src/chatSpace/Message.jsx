import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Send, Search, MoreVertical, Smile, Paperclip, Trash2 } from "lucide-react";

export default function Message({group,messages,isDark,isMobile,onBack,message,setMessage,handleSend,userId,onDeleteGroup,}) {

  const bottomRef = useRef(null);
  const [showMenu, setShowMenu] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const isCreator = group?.createdBy === userId;

  const handleDeleteClick = () => {
    setShowMenu(false);
    setShowDeleteModal(true);
  };

  const confirmDelete = () => {
    onDeleteGroup(group.id);
    setShowDeleteModal(false);
  };

  return (
    <div className="flex flex-col flex-1 min-w-0 w-full">
      <div className={`${isDark ? "bg-gray-800 border-gray-700" : "bg-white border-gray-200"} border-b p-4`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {isMobile && (
              <button
                onClick={onBack}
                className={`p-2 rounded-lg ${isDark ? "hover:bg-gray-700" : "hover:bg-gray-100"}`}
              >
                <ArrowLeft size={20} />
              </button>
            )}
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-xl">
              {group?.avatar || "💬"}
            </div>
            <h2 className={`font-semibold ${isDark ? "text-white" : "text-gray-900"}`}>
              {group?.name || "Group Chat"}
            </h2>
          </div>

          <div className="flex gap-2 relative">
            <button className={`p-2 rounded-lg ${isDark ? "hover:bg-gray-700" : "hover:bg-gray-100"}`}>
              <Search size={20} className={isDark ? "text-gray-400" : "text-gray-600"} />
            </button>
            
            {isCreator && (
              <>
                <button 
                  onClick={() => setShowMenu(!showMenu)}
                  className={`p-2 rounded-lg ${isDark ? "hover:bg-gray-700" : "hover:bg-gray-100"}`}
                >
                  <MoreVertical size={20} className={isDark ? "text-gray-400" : "text-gray-600"} />
                </button>

                {showMenu && (
                  <>
                    <div 
                      className="fixed inset-0 z-10" 
                      onClick={() => setShowMenu(false)}
                    />
                    <div className={`absolute right-0 top-12 z-20 w-48 rounded-lg shadow-lg ${isDark ? "bg-gray-700" : "bg-white"} border ${isDark ? "border-gray-600" : "border-gray-200"}`}>
                      <button
                        onClick={handleDeleteClick}
                        className={`w-full px-4 py-3 text-left flex items-center gap-3 rounded-lg ${isDark ? "hover:bg-gray-600 text-red-400" : "hover:bg-gray-50 text-red-600"}`}
                      >
                        <Trash2 size={18} />
                        <span className="font-medium">Delete Group</span>
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className={`flex-1 overflow-y-auto p-6 space-y-4 ${isDark ? "bg-gray-900" : "bg-gray-50"}`}>
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.isOwn ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-md px-4 py-2 rounded-2xl ${
                msg.isOwn
                  ? "bg-blue-500 text-white rounded-br-sm"
                  : isDark
                  ? "bg-gray-800 text-gray-100 rounded-bl-sm"
                  : "bg-white text-gray-800 rounded-bl-sm shadow-sm"
              }`}
            >
              <p className="text-sm">{msg.text}</p>
              <p className="text-xs mt-1 opacity-70">{msg.time}</p>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>


      <div className={`${isDark ? "bg-gray-800 border-gray-700" : "bg-white border-gray-200"} border-t p-4`}>
        <div className="flex items-end gap-2">
          <button className={`p-2 ${isDark ? "text-gray-400" : "text-gray-600"}`}>
            <Paperclip size={20} />
          </button>

          <div className={`flex-1 flex items-center gap-2 px-4 py-2 rounded-2xl ${isDark ? "bg-gray-700" : "bg-gray-100"}`}>
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Type a message..."
              className={`flex-1 bg-transparent outline-none ${isDark ? "text-white" : "text-gray-800"}`}
            />
            <button className={isDark ? "text-gray-400" : "text-gray-600"}>
              <Smile size={20} />
            </button>
          </div>

          <button
            onClick={handleSend}
            className="p-3 bg-blue-500 hover:bg-blue-600 rounded-full transition-colors"
          >
            <Send size={20} className="text-white" />
          </button>
        </div>
      </div>

      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className={`w-96 p-6 rounded-xl shadow-xl ${isDark ? "bg-gray-800" : "bg-white"}`}>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-red-100 rounded-full">
                <Trash2 size={24} className="text-red-600" />
              </div>
              <h3 className={`text-xl font-semibold ${isDark ? "text-white" : "text-gray-900"}`}>
                Delete Group?
              </h3>
            </div>
            
            <p className={`mb-6 ${isDark ? "text-gray-300" : "text-gray-600"}`}>
              Are you sure you want to delete "<strong>{group?.name}</strong>"? This will permanently delete all messages in this group. This action cannot be undone.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                  isDark 
                    ? "bg-gray-700 text-white hover:bg-gray-600" 
                    : "bg-gray-200 text-gray-800 hover:bg-gray-300"
                }`}
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}