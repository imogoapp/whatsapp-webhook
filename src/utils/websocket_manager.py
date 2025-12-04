from typing import Dict, Set
from fastapi import WebSocket
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # Armazena conexões por phone_number_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Armazena conexões globais (admin dashboard)
        self.global_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, phone_number_id: str = None):
        """Conecta cliente ao WebSocket"""
        await websocket.accept()
        
        if phone_number_id:
            # Conexão específica para um número
            if phone_number_id not in self.active_connections:
                self.active_connections[phone_number_id] = set()
            self.active_connections[phone_number_id].add(websocket)
            print(f"✓ Cliente conectado ao phone_number_id: {phone_number_id}")
        else:
            # Conexão global (recebe tudo)
            self.global_connections.add(websocket)
            print(f"✓ Cliente conectado globalmente")
    
    def disconnect(self, websocket: WebSocket, phone_number_id: str = None):
        """Desconecta cliente"""
        if phone_number_id and phone_number_id in self.active_connections:
            self.active_connections[phone_number_id].discard(websocket)
            if not self.active_connections[phone_number_id]:
                del self.active_connections[phone_number_id]
            print(f"✓ Cliente desconectado de: {phone_number_id}")
        else:
            self.global_connections.discard(websocket)
            print(f"✓ Cliente desconectado globalmente")
    
    async def broadcast_to_phone(self, phone_number_id: str, message: dict):
        """Envia mensagem para todos conectados em um phone_number_id"""
        if phone_number_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[phone_number_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Erro ao enviar para {phone_number_id}: {e}")
                    disconnected.add(connection)
            
            # Remove conexões mortas
            for conn in disconnected:
                self.active_connections[phone_number_id].discard(conn)
    
    async def broadcast_global(self, message: dict):
        """Envia mensagem para todos conectados globalmente"""
        disconnected = set()
        for connection in self.global_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Erro ao enviar globalmente: {e}")
                disconnected.add(connection)
        
        # Remove conexões mortas
        for conn in disconnected:
            self.global_connections.discard(conn)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Envia mensagem para um cliente específico"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Erro ao enviar mensagem pessoal: {e}")

# Instância global
manager = ConnectionManager()