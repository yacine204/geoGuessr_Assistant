from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation
from models.image import Image
from models.reply import Reply
from service.cloudinary import upload_image_to_cloudinary

async def InitConversation(
    user_id: int,
    image_bytes: bytes,
    guess_result: str,
    session: AsyncSession,
) -> Optional[Conversation]:
    new_convo = Conversation(user_id=user_id, title="New Conversation")
    session.add(new_convo)
    await session.flush()

    cloudinary_url = await upload_image_to_cloudinary(
        image_bytes,
        user_id=user_id,
        conversation_id=new_convo.conversation_id,
    )

    new_image = Image(
        conversation_id=new_convo.conversation_id,
        storage_key=cloudinary_url,
    )
    session.add(new_image)
    await session.flush()

    new_reply = Reply(
        image_id=new_image.image_id,
        content=guess_result,
        generated_at=datetime.utcnow()
    )
    session.add(new_reply)

    await session.commit()
    await session.refresh(new_convo)
    return new_convo


async def IncrementConversation(
    conversation_id: int,
    user_id: int,
    image_bytes: bytes,
    guess_result: str,
    session: AsyncSession,
) -> Optional[Conversation]:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        return None

    cloudinary_url = await upload_image_to_cloudinary(
        image_bytes,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    new_image = Image(
        conversation_id=conversation_id,
        storage_key=cloudinary_url
    )
    session.add(new_image)
    await session.flush()
    
    new_reply = Reply(
        image_id=new_image.image_id,
        content=guess_result,
        generated_at=datetime.utcnow()
    )
    session.add(new_reply)

    conversation.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(conversation)
    return conversation


async def DeleteConversation(conversation_id: int, session:AsyncSession)->bool:
    if conversation_id is None:
        return False
    
    stmt = delete(Conversation).where(Conversation.conversation_id == conversation_id)
    result = await session.execute(stmt)
   
    
    await session.commit()
    return result.rowcount > 0
    
async def GetUserConvos(user_id: int, session: AsyncSession) -> list[Conversation]:
    if user_id is None or session is None:
        return []
    
    stmt = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.created_at.desc())
    result = await session.execute(stmt)
    conversations = result.scalars().all()
    return conversations