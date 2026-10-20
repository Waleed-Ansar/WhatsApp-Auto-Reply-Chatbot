from typing import Dict
from asyncio import Lock
from langchain_classic.memory import ConversationBufferWindowMemory
from session import session_manager


class MemoryService:
    def __init__(self):
        self.user_memories: Dict[str, ConversationBufferWindowMemory] = {}
        self._lock = Lock()

    async def get_or_create_user_memory(
        self,
        chat_id: str,
        *,
        window_size: int = 100
    ) -> ConversationBufferWindowMemory:
        # if session_manager.session(chat_id) == "Expired":
        #     self.delete_user_memory(chat_id)

        if chat_id in self.user_memories:
            return self.user_memories[chat_id]

        async with self._lock:
            if chat_id not in self.user_memories:
                self.user_memories[chat_id] = ConversationBufferWindowMemory(
                    memory_key="chat_history",
                    return_messages=True,
                    k=window_size
                )

        return self.user_memories[chat_id]
    
    def get_user_slot_suggestions(self, chat_id: str):
        """Get slot suggestions for a specific user"""
        return self.user_slot_suggestions[chat_id]
    
    def set_user_slot_suggestions(self, chat_id: str, suggestions: list):
        """Set slot suggestions for a specific user"""
        self.user_slot_suggestions[chat_id] = suggestions
    
    def clear_user_slot_suggestions(self, chat_id: str):
        """Clear slot suggestions for a specific user"""
        self.user_slot_suggestions.pop(chat_id, None)
    
    def get_formatted_memory(self, chat_id: str):
        """Get formatted memory for API response"""
        memory = self.user_memories.get(chat_id)
        if not memory:
            return None
        
        messages = memory.chat_memory.messages
        formatted_memory = [
            {"type": msg.type, "content": msg.content} for msg in messages
        ]
        return formatted_memory
    
    def delete_user_memory(self, chat_id: str):
        """Delete memory for a specific user"""
        if chat_id in self.user_memories:
            del self.user_memories[chat_id]
            return True
        return False
    
    def get_all_chat_ids(self):
        """Get all chat IDs with stored memories"""
        return list(self.user_memories.keys())

memory_service = MemoryService()
