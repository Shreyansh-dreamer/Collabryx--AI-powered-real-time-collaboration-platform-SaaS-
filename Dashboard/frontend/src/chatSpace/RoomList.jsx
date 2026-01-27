import { memo, useCallback, useMemo, useState } from "react";
import { Search, Users } from "lucide-react";
import CreateRoom from "./CreateRoom";

export default function RoomList({groups,selectedChat,setSelectedChat,isDark,isMobile,showCreateGroup,setShowCreateGroup,newGroupName,setNewGroupName,newGroupPhoto,setNewGroupPhoto,handleCreateGroup,}) {
  const [imageErrors, setImageErrors] = useState({});
  const [search,setSearch] = useState("");

  const filteredGroups = useMemo(() => {
    const normalizedSearch = search.toLowerCase().replace(/\s+/g, "");
    if (!normalizedSearch) return groups;
    return groups.filter(group =>
      group.name
        .toLowerCase()
        .replace(/\s+/g, "")
        .includes(normalizedSearch)
    );
  }, [groups, search]);

  const getInitials = (name = "") => {
    return name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map(word => word[0].toUpperCase())
      .join("");
  };

  const gradients = useMemo(()=>[
    "from-pink-500 to-rose-500",
    "from-purple-500 to-indigo-500",
    "from-blue-500 to-cyan-500",
    "from-green-500 to-emerald-500",
    "from-orange-500 to-amber-500",
    "from-red-500 to-pink-500",
  ],[]);

  const getGradient = useCallback((seed = "") => {
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
      hash = seed.charCodeAt(i) + ((hash << 5) - hash);
    }
    return gradients[Math.abs(hash) % gradients.length];
  },[gradients]);

  const handleImageError = (groupId) => {
    setImageErrors(prev => ({ ...prev, [groupId]: true }));
  };

  const shouldShowImage = (group) => {
    return group.avatar && group.avatar !== "💬" && !imageErrors[group.id];
  };

  return (
    <div
      className={`${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} ${!isMobile ? 'border-r' : ''} flex flex-col`}
      style={{ width: isMobile ? '100%' : 'clamp(320px, 30vw, 500px)' }}
    >
      <div className={`p-4 ${isDark ? 'border-gray-700' : 'border-gray-200'} border-b`}>
        <h1 className={`lg:text-xl text-lg font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-800'}`}>
          Group Chats
        </h1>

        <CreateRoom
          isDark={isDark}
          showCreateGroup={showCreateGroup}
          setShowCreateGroup={setShowCreateGroup}
          newGroupName={newGroupName}
          setNewGroupName={setNewGroupName}
          newGroupPhoto={newGroupPhoto}
          setNewGroupPhoto={setNewGroupPhoto}
          handleCreateGroup={handleCreateGroup}
        />

        <div className="relative">
          <Search className={`absolute left-3 top-2.5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} size={20} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search groups..."
            className={`w-full pl-10 pr-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isDark ? 'bg-gray-700 text-white placeholder-gray-400' : 'bg-gray-100 text-gray-800'
            }`}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {filteredGroups.map((group) => (
          <div
            key={group.id}
            onClick={() => setSelectedChat(group.id)}
            className={`p-4 ${isDark ? 'border-gray-700' : 'border-gray-100'} border-b cursor-pointer transition-colors ${
              selectedChat === group.id
                ? isDark ? 'bg-gray-700' : 'bg-blue-50'
                : isDark ? 'hover:bg-gray-750' : 'hover:bg-gray-50'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-12 h-12 rounded-full flex-shrink-0 flex items-center justify-center text-white font-semibold text-sm bg-gradient-to-br ${getGradient(group.id || group.name)}`}>
                {shouldShowImage(group) ? (
                  <img
                    src={group.avatar}
                    alt={group.name}
                    className="w-full h-full object-cover rounded-full"
                    onError={() => handleImageError(group.id)}
                  />
                ) : (
                  getInitials(group.name)
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h3 className={`font-semibold truncate ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {group.name}
                  </h3>
                  <span className={`text-xs ml-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    {group.time}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <p className={`text-sm truncate ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    {group.lastMessage || "No messages yet"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}