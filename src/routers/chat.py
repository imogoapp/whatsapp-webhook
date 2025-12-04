from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from src.db.storage import db
router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

# Models
class MessageCreate(BaseModel):
    wa_id: str
    wa_id_received: str
    phone_number_id: str
    content: str
    is_user_message: bool = True

class MessageStatusUpdate(BaseModel):
    status: str  # sent, delivered, read, failed

class FlowStateUpdate(BaseModel):
    flow_state: dict

class SessionResponse(BaseModel):
    session_id: str
    wa_id: str
    wa_id_received: str
    phone_number_id: str
    message_count: int
    is_active: bool

# ==================== ENDPOINTS ====================

@router.get("/sessions/{wa_id}")
def get_user_sessions(
    wa_id: str,
    phone_number_id: str,
    limit: int = Query(10, ge=1, le=50)
):
    """Lista últimas sessões de um usuário"""
    sessions = db.get_user_sessions(wa_id, phone_number_id, limit)
    return {
        "wa_id": wa_id,
        "phone_number_id": phone_number_id,
        "total": len(sessions),
        "data": sessions
    }

@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    """Lista todas as mensagens de uma sessão"""
    messages = db.get_session_messages(session_id)
    
    if not messages:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return {
        "session_id": session_id,
        "total": len(messages),
        "messages": messages
    }

@router.get("/active-session")
def get_active_session(
    wa_id: str,
    wa_id_received: str,
    phone_number_id: str
):
    """Busca a sessão ativa (últimas 24h) de uma conversa"""
    session = db.get_active_session(wa_id, wa_id_received, phone_number_id)
    
    if not session:
        return {
            "success": False,
            "message": "Nenhuma sessão ativa encontrada",
            "data": None
        }
    
    return {
        "success": True,
        "message": "Sessão ativa encontrada",
        "data": session
    }

@router.post("/message")
def create_message(payload: MessageCreate):
    """Cria uma nova mensagem na sessão"""
    message = db.create_session_message(
        wa_id=payload.wa_id,
        wa_id_received=payload.wa_id_received,
        phone_number_id=payload.phone_number_id,
        content=payload.content,
        payload={"content": payload.content, "is_user_message": payload.is_user_message},
        is_user_message=payload.is_user_message,
        message_status='sent'
    )
    
    if not message:
        raise HTTPException(status_code=500, detail="Erro ao criar mensagem")
    
    return {
        "success": True,
        "message": "Mensagem criada com sucesso",
        "data": message
    }

@router.patch("/message/{message_id}/status")
def update_message_status(message_id: int, payload: MessageStatusUpdate):
    """Atualiza o status de uma mensagem"""
    valid_statuses = ['sent', 'delivered', 'read', 'failed']
    
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status inválido. Use: {', '.join(valid_statuses)}"
        )
    
    ok = db.update_message_status(message_id, payload.status)
    
    if not ok:
        raise HTTPException(status_code=500, detail="Erro ao atualizar status")
    
    return {
        "success": True,
        "message": f"Status atualizado para '{payload.status}'",
        "message_id": message_id
    }

@router.patch("/message/{message_id}/bot-reply")
def mark_bot_replied(message_id: int):
    """Marca que o bot respondeu a esta mensagem"""
    ok = db.mark_bot_replied(message_id)
    
    if not ok:
        raise HTTPException(status_code=500, detail="Erro ao marcar bot replied")
    
    return {
        "success": True,
        "message": "Bot reply marcado com sucesso",
        "message_id": message_id
    }

@router.patch("/message/{message_id}/flow-state")
def update_message_flow(message_id: int, payload: FlowStateUpdate):
    """Atualiza o estado do flow de uma mensagem"""
    ok = db.update_flow_state(message_id, payload.flow_state)
    
    if not ok:
        raise HTTPException(status_code=500, detail="Erro ao atualizar flow state")
    
    return {
        "success": True,
        "message": "Flow state atualizado com sucesso",
        "message_id": message_id
    }

@router.get("/conversation")
def get_conversation(
    wa_id: str,
    wa_id_received: str,
    phone_number_id: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Busca a conversa completa entre dois usuários"""
    sessions = db.get_user_sessions(wa_id, phone_number_id, limit)
    
    if not sessions:
        return {
            "wa_id": wa_id,
            "wa_id_received": wa_id_received,
            "phone_number_id": phone_number_id,
            "total_messages": 0,
            "sessions": [],
            "messages": []
        }
    
    # Coleta todas as mensagens de todas as sessões
    all_messages = []
    for session in sessions:
        messages = db.get_session_messages(session['session_id'])
        all_messages.extend(messages)
    
    # Ordena por data
    all_messages.sort(key=lambda x: x['create_in'])
    
    return {
        "wa_id": wa_id,
        "wa_id_received": wa_id_received,
        "phone_number_id": phone_number_id,
        "total_messages": len(all_messages),
        "total_sessions": len(sessions),
        "sessions": sessions,
        "messages": all_messages
    }

@router.get("/statistics/{phone_number_id}")
def get_chat_statistics(phone_number_id: str):
    """Retorna estatísticas de chat para um número"""
    # Busca todas as mensagens do número
    try:
        conn = db._get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Erro ao conectar ao banco")
        
        cur = conn.cursor(dictionary=True)
        
        # Total de mensagens
        cur.execute("""
            SELECT COUNT(*) as total FROM chat_session_message
            WHERE phone_number_id = %s
        """, (phone_number_id,))
        total_msgs = cur.fetchone()['total']
        
        # Mensagens por status
        cur.execute("""
            SELECT message_status, COUNT(*) as count
            FROM chat_session_message
            WHERE phone_number_id = %s
            GROUP BY message_status
        """, (phone_number_id,))
        status_dist = cur.fetchall()
        
        # Sessões ativas
        cur.execute("""
            SELECT COUNT(DISTINCT session_id) as count
            FROM chat_session_message
            WHERE phone_number_id = %s AND is_active = TRUE
        """, (phone_number_id,))
        active_sessions = cur.fetchone()['count']
        
        # Mensagens respondidas por bot
        cur.execute("""
            SELECT COUNT(*) as count FROM chat_session_message
            WHERE phone_number_id = %s AND bot_replied = TRUE
        """, (phone_number_id,))
        bot_replies = cur.fetchone()['count']
        
        # Mensagens do usuário vs bot
        cur.execute("""
            SELECT 
                SUM(CASE WHEN is_user_message = TRUE THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN is_user_message = FALSE THEN 1 ELSE 0 END) as bot_messages
            FROM chat_session_message
            WHERE phone_number_id = %s
        """, (phone_number_id,))
        message_types = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            "phone_number_id": phone_number_id,
            "total_messages": total_msgs,
            "user_messages": message_types['user_messages'] or 0,
            "bot_messages": message_types['bot_messages'] or 0,
            "active_sessions": active_sessions,
            "bot_replies": bot_replies,
            "status_distribution": status_dist
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@router.get("/active-chats/{phone_number_id}")
def get_active_chats(
    phone_number_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500)
):
    """Retorna todos os chats ativos (conversas) para um phone_number_id"""
    try:
        conn = db._get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Erro ao conectar ao banco")
        
        cur = conn.cursor(dictionary=True)
        
        # Busca todas as conversas ativas agrupadas por wa_id
        cur.execute("""
            SELECT 
                wa_id,
                phone_number_id,
                MAX(c.name) as contact_name,
                COUNT(DISTINCT csm.session_id) as total_sessions,
                COUNT(csm.id) as total_messages,
                SUM(CASE WHEN csm.is_user_message = TRUE THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN csm.is_user_message = FALSE THEN 1 ELSE 0 END) as bot_messages,
                SUM(CASE WHEN csm.bot_replied = TRUE THEN 1 ELSE 0 END) as bot_replies,
                MAX(csm.create_in) as last_message_at,
                MAX(CASE WHEN csm.is_active = TRUE THEN csm.expires_at END) as session_expires_at,
                MAX(csm.is_active) as has_active_session,
                MAX(CASE WHEN csm.message_status IN ('delivered', 'read') THEN csm.create_in END) as last_read_at
            FROM chat_session_message csm
            LEFT JOIN contacts c ON csm.wa_id = c.wa_id AND csm.phone_number_id = c.create_for_phone_number
            WHERE csm.phone_number_id = %s AND csm.is_active = TRUE
            GROUP BY csm.wa_id, csm.phone_number_id
            ORDER BY csm.create_in DESC
            LIMIT %s OFFSET %s
        """, (phone_number_id, limit, skip))
        
        chats = cur.fetchall()
        
        # Total de chats ativos
        cur.execute("""
            SELECT COUNT(DISTINCT wa_id) as total
            FROM chat_session_message
            WHERE phone_number_id = %s AND is_active = TRUE
        """, (phone_number_id,))
        
        total_chats = cur.fetchone()['total']
        
        cur.close()
        conn.close()
        
        # Formata resposta
        formatted_chats = []
        for chat in chats:
            formatted_chats.append({
                "wa_id": chat['wa_id'],
                "contact_name": chat['contact_name'] or "Desconhecido",
                "phone_number_id": chat['phone_number_id'],
                "total_sessions": chat['total_sessions'],
                "total_messages": chat['total_messages'],
                "user_messages": chat['user_messages'],
                "bot_messages": chat['bot_messages'],
                "bot_replies": chat['bot_replies'],
                "has_active_session": bool(chat['has_active_session']),
                "last_message_at": chat['last_message_at'].strftime('%Y-%m-%d %H:%M:%S') if chat['last_message_at'] else None,
                "last_read_at": chat['last_read_at'].strftime('%Y-%m-%d %H:%M:%S') if chat['last_read_at'] else None,
                "session_expires_at": chat['session_expires_at'].strftime('%Y-%m-%d %H:%M:%S') if chat['session_expires_at'] else None
            })
        
        return {
            "phone_number_id": phone_number_id,
            "total_active_chats": total_chats,
            "returned": len(formatted_chats),
            "skip": skip,
            "limit": limit,
            "data": formatted_chats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@router.get("/active-chats/{phone_number_id}/unread")
def get_unread_chats(
    phone_number_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500)
):
    """Retorna apenas os chats com mensagens não lidas"""
    try:
        conn = db._get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Erro ao conectar ao banco")
        
        cur = conn.cursor(dictionary=True)
        
        # Busca conversas com mensagens não lidas (status != 'read')
        cur.execute("""
            SELECT 
                wa_id,
                phone_number_id,
                MAX(c.name) as contact_name,
                COUNT(DISTINCT csm.session_id) as total_sessions,
                COUNT(csm.id) as total_messages,
                SUM(CASE WHEN csm.message_status NOT IN ('read', 'delivered') THEN 1 ELSE 0 END) as unread_count,
                SUM(CASE WHEN csm.is_user_message = TRUE THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN csm.is_user_message = FALSE THEN 1 ELSE 0 END) as bot_messages,
                MAX(csm.create_in) as last_message_at,
                MAX(csm.content) as last_message_content
            FROM chat_session_message csm
            LEFT JOIN contacts c ON csm.wa_id = c.wa_id AND csm.phone_number_id = c.create_for_phone_number
            WHERE csm.phone_number_id = %s 
              AND csm.is_active = TRUE
              AND csm.message_status NOT IN ('read', 'delivered')
            GROUP BY csm.wa_id, csm.phone_number_id
            ORDER BY csm.create_in DESC
            LIMIT %s OFFSET %s
        """, (phone_number_id, limit, skip))
        
        chats = cur.fetchall()
        
        # Total de chats com não lidos
        cur.execute("""
            SELECT COUNT(DISTINCT wa_id) as total
            FROM chat_session_message
            WHERE phone_number_id = %s 
              AND is_active = TRUE
              AND message_status NOT IN ('read', 'delivered')
        """, (phone_number_id,))
        
        total_unread_chats = cur.fetchone()['total']
        
        cur.close()
        conn.close()
        
        # Formata resposta
        formatted_chats = []
        for chat in chats:
            formatted_chats.append({
                "wa_id": chat['wa_id'],
                "contact_name": chat['contact_name'] or "Desconhecido",
                "phone_number_id": chat['phone_number_id'],
                "unread_count": chat['unread_count'],
                "total_messages": chat['total_messages'],
                "user_messages": chat['user_messages'],
                "bot_messages": chat['bot_messages'],
                "last_message_at": chat['last_message_at'].strftime('%Y-%m-%d %H:%M:%S') if chat['last_message_at'] else None,
                "last_message_content": chat['last_message_content']
            })
        
        return {
            "phone_number_id": phone_number_id,
            "total_unread_chats": total_unread_chats,
            "returned": len(formatted_chats),
            "skip": skip,
            "limit": limit,
            "data": formatted_chats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@router.get("/active-chats/{phone_number_id}/summary")
def get_chats_summary(phone_number_id: str):
    """Retorna um resumo de todos os chats do número"""
    try:
        conn = db._get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Erro ao conectar ao banco")
        
        cur = conn.cursor(dictionary=True)
        
        # Total de chats ativos
        cur.execute("""
            SELECT COUNT(DISTINCT wa_id) as total
            FROM chat_session_message
            WHERE phone_number_id = %s AND is_active = TRUE
        """, (phone_number_id,))
        total_active = cur.fetchone()['total']
        
        # Chats com não lidos
        cur.execute("""
            SELECT COUNT(DISTINCT wa_id) as total
            FROM chat_session_message
            WHERE phone_number_id = %s 
              AND is_active = TRUE
              AND message_status NOT IN ('read', 'delivered')
        """, (phone_number_id,))
        unread_chats = cur.fetchone()['total']
        
        # Estatísticas gerais
        cur.execute("""
            SELECT 
                COUNT(*) as total_messages,
                SUM(CASE WHEN is_user_message = TRUE THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN is_user_message = FALSE THEN 1 ELSE 0 END) as bot_messages,
                SUM(CASE WHEN bot_replied = TRUE THEN 1 ELSE 0 END) as bot_replies,
                COUNT(DISTINCT session_id) as total_sessions
            FROM chat_session_message
            WHERE phone_number_id = %s AND is_active = TRUE
        """, (phone_number_id,))
        
        stats = cur.fetchone()
        
        # Distribuição por status
        cur.execute("""
            SELECT message_status, COUNT(*) as count
            FROM chat_session_message
            WHERE phone_number_id = %s AND is_active = TRUE
            GROUP BY message_status
        """, (phone_number_id,))
        
        status_dist = {row['message_status']: row['count'] for row in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        return {
            "phone_number_id": phone_number_id,
            "summary": {
                "total_active_chats": total_active,
                "unread_chats": unread_chats,
                "total_messages": stats['total_messages'],
                "user_messages": stats['user_messages'],
                "bot_messages": stats['bot_messages'],
                "bot_replies": stats['bot_replies'],
                "total_sessions": stats['total_sessions']
            },
            "status_distribution": status_dist
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")