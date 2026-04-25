import service.conversation as conversation_service
from models.conversation import ConversationRead
from models.user import User
from fastapi import APIRouter, Depends, HTTPException, status, Path, UploadFile, File, Form
from database.db import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_current_user

router = APIRouter(prefix="/conversation", tags = ["conversation"])


@router.post('/init', response_model=ConversationRead)
async def Init(
    image: UploadFile = File(...),
    guess_result: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    image_bytes = await image.read()

    init = await conversation_service.InitConversation(
        current_user.id,
        image_bytes,
        guess_result,
        session,
    )
    if init is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversation initialization failed"
        )
    return init

@router.post('/increment/{conversation_id}', response_model=ConversationRead)
async def Increment(
    conversation_id: int = Path(..., alias="conversation_id"),
    image: UploadFile = File(...),
    guess_result: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    image_bytes = await image.read()

    incremented_convo = await conversation_service.IncrementConversation(
        conversation_id,
        current_user.id,
        image_bytes,
        guess_result,
        session,
    )
    if incremented_convo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversation incrementation failed"
        )
    return incremented_convo


@router.delete('/delete/{conversation_id}')
async def Delete(conversation_id: int = Path(..., alias="conversation_id")
                 ,session: AsyncSession = Depends(get_async_session)):
    
    deleted_convo = await conversation_service.DeleteConversation(conversation_id, session)
    if deleted_convo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="couldnt delete conversation"
        )
    return {"deleted conversation status": deleted_convo}

@router.get('/my_convos', response_model=list[ConversationRead])
async def MyConversations(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    conversations = await conversation_service.GetUserConvos(current_user.id, session)
    return conversations or []