import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from app.schemas.models import AnswerResponse, AskRequest
from app.agent.agents import agent
from app.agent.memory import memory_service
from app.core.config import config
from app.core.session import get_jwt_token


def extract_final_answer(response):
    if isinstance(response, str):
        return response

    if isinstance(response, list):
        for item in reversed(response):
            if (
                isinstance(item, dict)
                and item.get("type") == "text"
                and item.get("phase") == "final_answer"
            ):
                return item.get("text", "")

        # Fallback: collect ordinary text blocks
        return "\n".join(
            item["text"]
            for item in response
            if isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
        )

    return str(response) if response is not None else ""

app = FastAPI(title="RTD Property LLM RAG API with ChatGroq")

@app.get('/')
async def from_root():
    return {"message": "Hello from root of RTD"}

@app.get('/chat')
async def from_chat():
    return {"message": " Memory working and Adding Cancel appointment"}

@app.get('/get-auth-token')
async def get_auth_token():
    expiry, token = await get_jwt_token()
    
    return {
        "expire time": expiry,
        "token": token
    }

@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: AskRequest):
    try:
        if not request.chat_id:
            return AnswerResponse(status=False, query=request.query, answer="User ID must not be empty.")

        contact_id = request.chat_id
        
        query = request.query
        
        llm_input = f"{query}. Chat ID: {contact_id}"
    
        agent_executor = await agent.get_agent_executor(contact_id)
        
        result = await agent_executor.ainvoke({"input": llm_input})
        
        if result is not None:
            return AnswerResponse(
                status=True, 
                query=query, 
                answer = extract_final_answer(result.get("output"))
            )
        
        return AnswerResponse(
                status=False,
                query=request.query, 
                answer="An error has occurred."
            )
    except Exception as e:
        return AnswerResponse(status=False, query=request.query, answer=str(e))

@app.get("/check-slot/{chat_id}")
async def check_slot_availability(chat_id: str):
    token_expiry, token = await get_jwt_token()
    time_now = datetime.now(timezone.utc)

    if time_now > token_expiry:
        token_expiry, token = await get_jwt_token()
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    contact_id = chat_id
    # contact_id = "jrNeTQ4kB_FeIvbXH3tKkA"
    start_time = "2024-02-03T01:00Z"
    end_time = "2050-02-04T01:30Z"

    params = {
        "contactId": contact_id,
        "startTime": datetime.fromisoformat(start_time),
        "endTime": datetime.fromisoformat(end_time)
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{config.API_BASE_URL}/api/GoogleCalendar/CheckSlotAvailability", params=params, headers=headers)
        response_data = response.json()

        if response_data.get("success") == True:
            return response_data
        
        return response_data

@app.get("/memory/{chat_id}")
async def get_user_memory(chat_id: str):
    formatted_memory = memory_service.get_formatted_memory(chat_id)
    if not formatted_memory:
        return JSONResponse(
            content={"status": "False", "message": f"No memory found for chat_id '{chat_id}'."},
            status_code=404
        )

    return {
        "status": "True",
        "chat_id": chat_id,
        "chat_history": formatted_memory
    }

@app.delete("/memory/{chat_id}")
async def delete_user_memory(chat_id: str):
    if memory_service.delete_user_memory(chat_id):
        return JSONResponse(content={"status": "True", "message": f"Memory for chat_id '{chat_id}' deleted."})
    else:
        return JSONResponse(
            content={"status": "False", "message": f"No memory found for chat_id '{chat_id}'."},
            status_code=404
        )

@app.get("/users")
def get_all_users():
    return {
        "status": "True",
        "chat_ids": memory_service.get_all_chat_ids()
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}