import { Plus, X } from "lucide-react";
import { useState } from "react";
import { useTheme } from '../ThemeContext.jsx';

export default function CreateRoom({showCreateGroup,setShowCreateGroup,newGroupName,setNewGroupName,newGroupPhoto,setNewGroupPhoto,handleCreateGroup,}) {
  const { isDark } = useTheme();
  const [imageError, setImageError] = useState(false);

  const handleImageError = () => {
    setImageError(true);
  };

  const handlePhotoChange = (e) => {
    setNewGroupPhoto(e.target.value);
    setImageError(false);
  };

  const getInitials = (name = "") => {
    return name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map(word => word[0].toUpperCase())
      .join("");
  };

  const gradients = [
    "from-pink-500 to-rose-500",
    "from-purple-500 to-indigo-500",
    "from-blue-500 to-cyan-500",
    "from-green-500 to-emerald-500",
    "from-orange-500 to-amber-500",
    "from-red-500 to-pink-500",
  ];

  const getGradient = (seed = "") => {
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
      hash = seed.charCodeAt(i) + ((hash << 5) - hash);
    }
    return gradients[Math.abs(hash) % gradients.length];
  };

  const showImagePreview = newGroupPhoto && !imageError;
  const showInitials = newGroupName && (!newGroupPhoto || imageError);

  return (
    <>
      {!showCreateGroup ? (
        <button 
          onClick={() => setShowCreateGroup(true)}
          className="w-full mb-4 px-4 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-xl font-medium flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40"
        >
          <Plus size={20} />
          <span>Create New Group</span>
        </button>
      ) : (
        <div className={`mb-4 p-4 rounded-xl ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
          <div className="flex items-center justify-between mb-3">
            <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-gray-800'}`}>
              New Group
            </h3>
            <button
              onClick={() => {
                setShowCreateGroup(false);
                setImageError(false);
              }}
              className={`p-1 rounded-lg transition-colors ${isDark ? 'hover:bg-gray-600' : 'hover:bg-gray-200'}`}
            >
              <X size={18} className={isDark ? 'text-gray-400' : 'text-gray-600'} />
            </button>
          </div>

          <input
            type="text"
            placeholder="Group Name"
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
            className={`w-full px-3 py-2 mb-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isDark ? 'bg-gray-600 text-white placeholder-gray-400' : 'bg-white text-gray-800 border border-gray-300'
            }`}
          />

          <input
            type="url"
            placeholder="Profile Photo URL (optional)"
            value={newGroupPhoto}
            onChange={handlePhotoChange}
            className={`w-full px-3 py-2 mb-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isDark ? 'bg-gray-600 text-white placeholder-gray-400' : 'bg-white text-gray-800 border border-gray-300'
            }`}
          />

          {/* Preview */}
          <div className="mb-2 flex justify-center">
            {showImagePreview ? (
              <img 
                src={newGroupPhoto} 
                alt="Preview" 
                className="w-16 h-16 rounded-full object-cover"
                onError={handleImageError}
              />
            ) : showInitials ? (
              <div className={`w-16 h-16 rounded-full flex items-center justify-center text-white font-semibold text-lg bg-gradient-to-br ${getGradient(newGroupName)}`}>
                {getInitials(newGroupName)}
              </div>
            ) : (
              <div className={`w-16 h-16 rounded-full flex items-center justify-center text-3xl ${isDark ? 'bg-gray-600' : 'bg-gray-200'}`}>
                💬
              </div>
            )}
          </div>

          {imageError && newGroupPhoto && (
            <div className={`mb-2 text-center text-xs ${isDark ? 'text-yellow-400' : 'text-yellow-600'}`}>
              ⚠️ Image failed to load - showing initials instead
            </div>
          )}

          <p className={`text-xs mb-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            💡 Image URL is optional. If not provided or fails to load, group initials will be displayed.
          </p>

          <button
            onClick={handleCreateGroup}
            disabled={!newGroupName.trim()}
            className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
          >
            Create Group
          </button>
        </div>
      )}
    </>
  );
}