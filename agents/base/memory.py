# agents/base/memory.py

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from backend.config.database import SupabaseClient
import json


class AgentMemory:
    """Enhanced memory management for agents using Supabase"""
    
    def __init__(
        self,
        agent_id: str,
        tenant_id: str,
        max_short_term_messages: int = 20
    ):
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.max_short_term_messages = max_short_term_messages
        self.db_client = SupabaseClient(tenant_id=tenant_id)
        
        # Short-term memory (in-memory storage)
        self.short_term: List[Dict[str, Any]] = []
        
    async def add_message(self, content: str, role: str = "user"):
        """Add a message to memory"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to short-term memory
        self.short_term.append(message)
        
        # Trim if exceeds max
        if len(self.short_term) > self.max_short_term_messages:
            self.short_term = self.short_term[-self.max_short_term_messages:]
        
        # Store in database for long-term retention
        await self._store_in_database(message)
    
    async def get_relevant_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant context from memory"""
        contexts = []
        
        # Get from short-term memory
        recent_messages = self.short_term[-limit:]
        for msg in recent_messages:
            contexts.append({
                "type": "recent",
                "content": msg["content"],
                "role": msg["role"]
            })
        
        # Get from long-term memory
        stored_contexts = await self._retrieve_from_database(query, limit)
        contexts.extend(stored_contexts)
        
        return contexts
    
    async def _store_in_database(self, message: Dict[str, Any]):
        """Store message in database for long-term retention"""
        await self.db_client.insert("agent_memories", {
            "agent_id": self.agent_id,
            "role": message["role"],
            "content": message["content"],
            "timestamp": message["timestamp"]
        })
    
    async def _retrieve_from_database(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Retrieve relevant memories from database"""
        # Simple retrieval - in production, you might use vector search
        results = await self.db_client.select(
            "agent_memories",
            filters={"agent_id": self.agent_id},
            limit=limit
        )
        
        return [
            {
                "type": "stored",
                "content": r["content"],
                "role": r["role"]
            }
            for r in results
        ]
    
    def summarize_recent(self, num_messages: int = 10) -> str:
        """Summarize recent conversation"""
        messages = self.short_term[-num_messages:]
        summary = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            summary.append(f"{role}: {msg['content'][:100]}...")
        return "\n".join(summary)
    
    def clear_short_term(self):
        """Clear short-term memory"""
        self.short_term = []
    
    def export_memory(self) -> Dict[str, Any]:
        """Export memory state"""
        return {
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "short_term": self.short_term,
            "message_count": len(self.short_term)
        }

