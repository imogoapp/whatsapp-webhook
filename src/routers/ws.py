from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from src.utils.websocket_manager import manager

router = APIRouter(
    tags=["WebSocket"]
)

@router.websocket("/ws/chat/{phone_number_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    phone_number_id: str
):
    """WebSocket para receber mensagens de um phone_number_id específico"""
    await manager.connect(websocket, phone_number_id)
    
    try:
        # Envia mensagem de boas-vindas
        await manager.send_personal_message({
            "type": "connection",
            "status": "connected",
            "phone_number_id": phone_number_id,
            "message": f"Conectado ao chat {phone_number_id}"
        }, websocket)
        
        # Mantém conexão aberta
        while True:
            # Recebe mensagens do cliente (se necessário)
            data = await websocket.receive_text()
            
            # Pode processar comandos do cliente aqui
            # Exemplo: marcar mensagem como lida
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, phone_number_id)
        print(f"Cliente desconectado de {phone_number_id}")

@router.websocket("/ws/global")
async def websocket_global_endpoint(websocket: WebSocket):
    """WebSocket global - recebe todas as mensagens"""
    await manager.connect(websocket)
    
    try:
        await manager.send_personal_message({
            "type": "connection",
            "status": "connected",
            "message": "Conectado globalmente - recebendo todas as mensagens"
        }, websocket)
        
        while True:
            data = await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Cliente global desconectado")

@router.websocket("/ws/chats/{phone_number_id}")
async def websocket_chats_list_endpoint(
    websocket: WebSocket,
    phone_number_id: str
):
    """WebSocket para receber atualizações da lista de chats"""
    await manager.connect(websocket, f"chats_{phone_number_id}")
    
    try:
        await manager.send_personal_message({
            "type": "connection",
            "status": "connected",
            "phone_number_id": phone_number_id,
            "message": "Conectado à lista de chats"
        }, websocket)
        
        while True:
            data = await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"chats_{phone_number_id}")