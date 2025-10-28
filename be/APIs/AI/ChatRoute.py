"""
AI Chat API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List


from Schemas.AI import ChatMessage, ChatResponse, ConversationHistory
from AI.agent import get_agent
from APIs.Core import get_current_user, get_db
from Models.Admin.User import User
from Models.AI import ChatHistory as ChatHistoryModel

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with AI assistant

    The AI can:
    - Answer questions about projects and data
    - Execute actions (create projects, search inventory, etc.)
    - Answer questions based on uploaded documents
    - Provide insights and analysis

    Args:
        request: Chat message with optional context
        current_user: Authenticated user
        db: Database session

    Returns:
        AI response with actions and data
    """
    try:
        print("Chat request received")
        agent = get_agent()
        print("Chat request received2")

        response = agent.chat(
            message=request.message,
            user_id=current_user.id,
            db=db,
            conversation_id=request.conversation_id,
            project_context=request.project_context
        )
        print("Chat request received3")
        return ChatResponse(
            response=response['response'],
            conversation_id=response['conversation_id'],
            actions_taken=response['actions_taken'],
            data=response.get('data'),
            sources=response.get('sources')
        )

    except Exception as e:
        logger.error(f"Chat error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get conversation history

    Args:
        conversation_id: Conversation UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Conversation history with all messages
    """
    try:
        messages = db.query(ChatHistoryModel).filter(
            ChatHistoryModel.conversation_id == conversation_id,
            ChatHistoryModel.user_id == current_user.id
        ).order_by(ChatHistoryModel.timestamp.asc()).all()

        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        message_list = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "function_calls": msg.function_calls
            }
            for msg in messages
        ]

        return ConversationHistory(
            conversation_id=conversation_id,
            messages=message_list,
            created_at=messages[0].timestamp,
            last_message_at=messages[-1].timestamp,
            message_count=len(messages)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving conversation: {str(e)}"
        )


@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20
):
    """
    List user's recent conversations

    Args:
        current_user: Authenticated user
        db: Database session
        limit: Max conversations to return

    Returns:
        List of conversation summaries
    """
    try:
        # Get distinct conversation IDs with their latest message
        from sqlalchemy import func, distinct

        subquery = db.query(
            ChatHistoryModel.conversation_id,
            func.max(ChatHistoryModel.timestamp).label('last_message')
        ).filter(
            ChatHistoryModel.user_id == current_user.id
        ).group_by(
            ChatHistoryModel.conversation_id
        ).subquery()

        conversations = db.query(
            ChatHistoryModel.conversation_id,
            subquery.c.last_message,
            func.count(ChatHistoryModel.id).label('message_count')
        ).join(
            subquery,
            ChatHistoryModel.conversation_id == subquery.c.conversation_id
        ).filter(
            ChatHistoryModel.user_id == current_user.id
        ).group_by(
            ChatHistoryModel.conversation_id,
            subquery.c.last_message
        ).order_by(
            subquery.c.last_message.desc()
        ).limit(limit).all()

        # Get first user message for each conversation as preview
        result = []
        for conv_id, last_msg, msg_count in conversations:
            first_message = db.query(ChatHistoryModel).filter(
                ChatHistoryModel.conversation_id == conv_id,
                ChatHistoryModel.role == 'user'
            ).order_by(ChatHistoryModel.timestamp.asc()).first()

            result.append({
                "conversation_id": conv_id,
                "last_message_at": last_msg.isoformat(),
                "message_count": msg_count,
                "preview": first_message.content[:100] + "..." if first_message and len(first_message.content) > 100 else first_message.content if first_message else ""
            })

        return {
            "conversations": result,
            "total": len(result)
        }

    except Exception as e:
        logger.error(f"Error listing conversations for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing conversations: {str(e)}"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation

    Args:
        conversation_id: Conversation UUID to delete
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    try:
        # Delete all messages in conversation
        deleted = db.query(ChatHistoryModel).filter(
            ChatHistoryModel.conversation_id == conversation_id,
            ChatHistoryModel.user_id == current_user.id
        ).delete()

        if deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        db.commit()

        return {
            "success": True,
            "message": f"Deleted conversation with {deleted} messages"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting conversation: {str(e)}"
        )
