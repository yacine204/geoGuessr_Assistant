import service.conversation as conversation_service
from models.conversation import ConversationRead
from models.user import User
from fastapi import APIRouter, Depends, HTTPException, status, Path, UploadFile, File, Form
from database.db import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_current_user

router = APIRouter(prefix="/conversation", tags = ["conversation"])


@router.post(
    '/init',
    response_model=ConversationRead,
    summary="Create a conversation",
    description="Creates a new conversation for the authenticated user and stores the first image + guess result.",
)
async def Init(
    image: UploadFile = File(..., description="Image file for the first conversation message"),
    guess_result: str = Form(..., description="Serialized guess result payload"),
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

@router.post(
    '/increment/{conversation_id}',
    response_model=ConversationRead,
    summary="Append to an existing conversation",
    description="Adds a new image + guess result to a specific conversation owned by the authenticated user.",
)
async def Increment(
    conversation_id: int = Path(..., alias="conversation_id"),
    image: UploadFile = File(..., description="Image file to append"),
    guess_result: str = Form(..., description="Serialized guess result payload"),
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


@router.post(
    '/message',
    response_model=ConversationRead,
    summary="Create or append conversation message",
    description="If `conversation_id` is provided, appends to that conversation. Otherwise reuses latest conversation or creates a new one.",
)
async def Message(
    image: UploadFile = File(..., description="Image file for this message"),
    guess_result: str = Form(..., description="Serialized guess result payload"),
    conversation_id: int | None = Form(default=None, description="Optional target conversation id"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    image_bytes = await image.read()

    target_conversation_id = conversation_id
    if target_conversation_id is None:
        conversations = await conversation_service.GetUserConvos(current_user.id, session)
        if conversations:
            target_conversation_id = conversations[0].conversation_id

    if target_conversation_id is None:
        conversation = await conversation_service.InitConversation(
            current_user.id,
            image_bytes,
            guess_result,
            session,
        )
    else:
        conversation = await conversation_service.IncrementConversation(
            target_conversation_id,
            current_user.id,
            image_bytes,
            guess_result,
            session,
        )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found for this user",
        )

    return conversation


@router.delete(
    '/delete/{conversation_id}',
    summary="Delete a conversation",
    description="Deletes a conversation by id.",
)
async def Delete(conversation_id: int = Path(..., alias="conversation_id")
                 ,session: AsyncSession = Depends(get_async_session)):
    
    deleted_convo = await conversation_service.DeleteConversation(conversation_id, session)
    if deleted_convo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="couldnt delete conversation"
        )
    return {"deleted conversation status": deleted_convo}

@router.get(
    '/my_convos',
    response_model=list[ConversationRead],
    summary="List my conversations",
    description="Returns all conversations for the authenticated user.",
)
async def MyConversations(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    conversations = await conversation_service.GetUserConvos(current_user.id, session)
    return conversations or []