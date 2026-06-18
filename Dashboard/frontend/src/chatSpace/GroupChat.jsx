import { useEffect, useState, useMemo, useCallback } from "react";
import RoomList from "./RoomList";
import Message from "./Message";
import axios from 'axios';
import socket from "../Socket";
import { useTheme } from '../ThemeContext.jsx';

export default function GroupChat() {
  const { isDark } = useTheme();
  const [selectedChat, setSelectedChat] = useState(null);
  const [message, setMessage] = useState("");
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupPhoto, setNewGroupPhoto] = useState("");
  const [isMobile, setIsMobile] = useState(false);
  const [groups, setGroups] = useState([]);
  const [messages, setMessages] = useState([]);
  const [userId,setUserId] = useState("");


  useEffect(() => {
    if (!socket.connected) socket.connect();

    const handleAuth = ({ userId }) => {
      setUserId(userId);
    };

    const handleNewMessage = ({ id, senderId, content, createdAt }) => {
      setMessages(prev => [
        ...prev,
        {
          id,
          text: content,
          isOwn: senderId === userId,
          time: new Date(createdAt).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        },
      ]);
    };

    socket.on("auth-info", handleAuth);
    socket.on("new-message", handleNewMessage);

    return () => {
      socket.off("auth-info", handleAuth);
      socket.off("new-message", handleNewMessage);
    };
  }, [userId]); 

  useEffect(() => {
    if (!selectedChat) return;
    const roomId = selectedChat;
    if (!roomId) return;
    socket.emit("join-room", roomId);
    return () => {
      socket.emit("leaveRoom", roomId);
    };
  }, [selectedChat]);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) return;
    try {
      const res = await axios.post(
        "http://localhost:3000/createRoom",
        { name: newGroupName, image: newGroupPhoto },
        { withCredentials: true }
      );
      const newRoom = {
        id: res.data._id,
        name: res.data.name,
        avatar: res.data.image || "💬",
        lastMessage: "",
        time: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        unread: 0,
      };
      setNewGroupName("");
      setNewGroupPhoto("");
      setShowCreateGroup(false);
      setGroups(prev => [newRoom, ...prev]); 
    } catch (err) {
      console.error("Room could not be created:", err.response?.data || err.message);
    }
  };

  const getGroups = async () => {
    try {
      const res = await axios.get("http://localhost:3000/rooms", {
        withCredentials: true,
      });

      const formatted = res.data.map((room) => ({
        id: room._id,
        name: room.name,
        avatar: room.image || "💬",
        lastMessage: room.lastmsg || "",
        time: new Date(room.updatedAt).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        unread: 0,
        createdBy: room.createdBy,
      }));

      setGroups(formatted);
    } catch (err) {
      console.error("Fetch rooms failed:", err.response?.data || err.message);
    }
  };

  const handleDeleteGroup = useCallback(async (roomId) => {
    try {
      await axios.delete(`http://localhost:3000/rooms/${roomId}/delete`, {
        withCredentials: true,
      });
      setGroups(prev => prev.filter(g => g.id !== roomId));
      if (selectedChat === roomId) {
        setSelectedChat(null);
        setMessages([]);
      }
    } catch (err) {
      console.error("Delete group failed:", err.response?.data || err.message);
      alert(err.response?.data?.message || "Failed to delete group");
    }
  },[selectedChat]);

  useEffect(() => {
    getGroups();
  }, []);

  useEffect(() => {
    if (selectedChat === null) return;

    const fetchMessages = async () => {
      try {
        const roomId = selectedChat;
        const res = await axios.get(
          `http://localhost:3000/rooms/${roomId}`,
          { withCredentials: true }
        );
        const formatted = res.data.map(msg => ({
          id: msg._id,
          text: msg.content,
          isOwn: msg.senderId === userId,
          time: new Date(msg.createdAt).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        }));
        setMessages(formatted);
      } catch (err) {
        console.error("Fetch messages failed:", err.response?.data || err.message);
      }
    };

    fetchMessages();
  }, [selectedChat, userId]);

  const handleSend = useCallback(() => {
    if (!message.trim() || !selectedChat) return;
    socket.emit("send-message", {
      roomId: selectedChat,
      content: message,
    });
    setMessage("");
  },[message,selectedChat]);

  const showSidebar = !isMobile || selectedChat === null;
  const showChat = !isMobile || selectedChat !== null;
  const currentGroup = useMemo(
    ()=>groups.find(g => g.id === selectedChat),
    [groups,selectedChat]
  );

  return (
    <div className={`pt-18 flex h-screen w-screen overflow-hidden ${isDark ? 'bg-gray-900' : 'bg-gray-100'}`}>
      {showSidebar && (
        <RoomList
          groups={groups}
          selectedChat={selectedChat}
          setSelectedChat={setSelectedChat}
          isMobile={isMobile}
          showCreateGroup={showCreateGroup}
          setShowCreateGroup={setShowCreateGroup}
          newGroupName={newGroupName}
          setNewGroupName={setNewGroupName}
          newGroupPhoto={newGroupPhoto}
          setNewGroupPhoto={setNewGroupPhoto}
          handleCreateGroup={handleCreateGroup}
        />
      )}

      {showChat && (
        selectedChat !== null && currentGroup ? (
          <Message
            group={currentGroup}
            messages={messages}
            isMobile={isMobile}
            onBack={() => setSelectedChat(null)}
            message={message}
            setMessage={setMessage}
            handleSend={handleSend}
            userId={userId}
            onDeleteGroup={handleDeleteGroup}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-6xl mb-4">💬</div>
              <h2 className={`text-xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-800'}`}>
                Select a chat to start messaging
              </h2>
              <p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                Choose a group from the sidebar to view messages
              </p>
            </div>
          </div>
        )
      )}
    </div>
  );
}