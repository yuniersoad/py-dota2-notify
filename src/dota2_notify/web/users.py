from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/users")

@router.get("/")
async def get_users(request: Request):
    return await request.app.state.user_service.get_all_users_async()

@router.get("/{user_id}")
async def get_user(user_id: int, request: Request):
    user = await request.app.state.user_service.get_user_async(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user