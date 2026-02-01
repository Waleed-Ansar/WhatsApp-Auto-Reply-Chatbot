import httpx
from datetime import timedelta, timezone, datetime
from mcp.server.fastmcp import FastMCP
import pyodbc
import json
from config import config
from datetime_utils import has_time_info
from memory_service import memory_service
from models import AnswerResponse
from token_manager import get_jwt_token


mcp = FastMCP("RTD Chatbot")

api_base_url = config.API_BASE_URL
# contact_id = "LGh629GSeiq4A3Qocf7bIg"

@mcp.tool()    
async def check_slot_availability( contact_id: str, start_time: str, end_time: str):
    token_expiry, token = await get_jwt_token()
    time_now = datetime.now(timezone.utc)

    if time_now > token_expiry:
        token_expiry, token = await get_jwt_token()
        print(token)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    """Check if a time slot is available"""
    params = {
        "contactId": contact_id,
        "startTime": start_time,
        "endTime": end_time
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{api_base_url}/api/GoogleCalendar/CheckSlotAvailability",
            params=params,
            headers=headers
        )
        return response.json()

@mcp.tool()
async def book_appointment( contact_id: str, start_time: str, end_time: str, query: str):
    token_expiry, token = await get_jwt_token()
    time_now = datetime.now(timezone.utc)

    if time_now > token_expiry:
        token_expiry, token = await get_jwt_token()
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    """Book an appointment"""
    booking_payload = {
        "contactId": contact_id,
        "startTime": start_time,
        "endTime": end_time,
        "summary": "RTD Real Estate Appointment",
        "description": f"Booked via RTD AI Assistant: {query}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_base_url}/api/GoogleCalendar/BookAppointment",
            json=booking_payload,
            headers=headers
        )
        return response.json()



@mcp.tool()
async def check_cancel_appointment( contact_id: str, start_time: str, end_time: str):
    token_expiry, token = await get_jwt_token()
    time_now = datetime.now(timezone.utc)

    if time_now > token_expiry:
        token_expiry, token = await get_jwt_token()
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    """Cancel an appointment"""
    params = {
        "contactId": contact_id,
        "startTime": start_time,
        "endTime": end_time
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_base_url}/api/GoogleCalendar/CancelAppointmentAsync",
            json=params,
            headers=headers
        )
        try:
            return response.json()
        except Exception:
            return {
                "success": False,
                "message": f"Invalid response: {response.text}"
            }

@mcp.tool()
async def cancel_appointment( contact_id: str, start_time: str, end_time: str):
    token_expiry, token = await get_jwt_token()
    time_now = datetime.now(timezone.utc)

    if time_now > token_expiry:
        token_expiry, token = await get_jwt_token()
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    """Cancel an appointment"""
    params = {
        "contactId": contact_id,
        "startTime": start_time,
        "endTime": end_time
    }

    async with httpx.AsyncClient() as client:
        response = await client.request(
            "DELETE",
            f"{api_base_url}/api/GoogleCalendar/CancelAppointmentAsync",
            params=params,
            headers=headers
        )

        print("Status:", response.status_code)
        print("Response:", response.text)

        if response.status_code == 200:
            result = response.json()
            return result.get("success", False)
        return {False,response}



@mcp.tool()
async def handle_suggested_slot_booking( request, parsed_time):
    """Handle booking when user selects from suggested slots"""
    contact_id = request.get("chat_id")
    query = request.get("query")
    suggestions = memory_service.get_user_slot_suggestions(contact_id)
    parsed_time = datetime.fromisoformat(str(parsed_time))
    
    if suggestions and parsed_time:
        for start, end in suggestions:
            if abs((parsed_time - start).total_seconds()) < config.SLOT_TOLERANCE_SECONDS:
                booking_response = await book_appointment(
                    contact_id,
                    start.isoformat() + "Z",
                    end.isoformat() + "Z",
                    query
                )
                
                if booking_response.get("success") == True:
                    memory_service.clear_user_slot_suggestions(contact_id)
                    return AnswerResponse(
                        status=True,
                        query=query,
                        answer=f"✅ Appointment booked successfully for suggested time {parsed_time}."
                    )
                else:
                    return AnswerResponse(
                        status=False,
                        query=query,
                        answer="❌ Failed to book appointment for suggested slot."
                    )
    return None

@mcp.tool()
async def handle_direct_booking( request, parsed_time):
    """Handle direct appointment booking"""
    query = request.get("query")
    parsed_time = datetime.fromisoformat(str(parsed_time))

    if not (parsed_time and has_time_info(parsed_time)):
        return AnswerResponse(
            status=True,
            query=query,
            answer=(
                "🕒 Please provide the both date and time you want to book an appointment.\n\n"

            )
        )

    contact_id = request.get("chat_id")
    start_time = parsed_time.isoformat() + "Z"
    end_time = (parsed_time + timedelta(minutes=config.DEFAULT_APPOINTMENT_DURATION_MINUTES)).isoformat() + "Z"
    
    availability_data = await check_slot_availability(contact_id, start_time, end_time)
    
    if availability_data.get("success"):
        if availability_data.get("data", {}).get("isAvailable"):
            booking_response = await book_appointment(contact_id, start_time, end_time, query)
            
            if booking_response.get("success") == True:
                return AnswerResponse(
                    status=True,
                    query=query,
                    answer=f"✅ Appointment booked successfully for {parsed_time}!"
                )
            else:
                return AnswerResponse(
                    status=False,
                    query=query,
                    answer="❌ Failed to book appointment."
                )
        else:
            return await handle_unavailable_slot(request, availability_data, contact_id)
    else:
        return AnswerResponse(
            status=True,
            query=query,
            answer=availability_data.get("message")
        )

@mcp.tool()
async def handle_unavailable_slot( request, availability_data, contact_id):
    """Handle when requested slot is unavailable"""
    availability = availability_data.get("data", {})
    suggestions = availability.get("suggestions", [])
    query = request.get("query")
    # parsed_time = datetime.fromisoformat(str(parsed_time))
    
    if suggestions:
        parsed_suggestions = []
        for s in suggestions:
            s_start = datetime.fromisoformat(s["start"].replace("Z", "+00:00"))
            s_end = datetime.fromisoformat(s["end"].replace("Z", "+00:00"))
            parsed_suggestions.append((s_start, s_end))
        
        memory_service.set_user_slot_suggestions(contact_id, parsed_suggestions)
        
        natural_suggestions = []
        for s_start, _ in parsed_suggestions:
            natural_suggestions.append(f"- {s_start}")
        
        suggest_in_natural = "\n".join(natural_suggestions)
        return AnswerResponse(
            status=True,
            query=query,
            answer=f"🕒 That slot is not available. Here are some alternative slots:\n\n{suggest_in_natural}\n\n👉 Please reply with one of them to confirm your booking. \n\n Please keep the Format: \n\n book appointment for any above suggested slots"
        )
    else:
        return AnswerResponse(
            status=True,
            query=query,
            answer="❌ That slot is not available and no suggestions were found."
        )

@mcp.tool()
async def handle_slot_availability_check( request, parsed_time):
    """Handle slot availability checking"""
    if isinstance(request, str):
        raise TypeError("Expected full AskRequest object, got a string")

    query = request.get("query")
    parsed_time = datetime.fromisoformat(str(parsed_time))

    if not (parsed_time and has_time_info(parsed_time)):
        return AnswerResponse(
            status=True,
            query=query,
            answer=(
                "🕒 Please provide the both date and time you want check the slots availability.\n\n"

            )
        )

    contact_id = request.get("chat_id")
    start_time = parsed_time.isoformat() + "Z"
    end_time = (parsed_time + timedelta(minutes=config.DEFAULT_APPOINTMENT_DURATION_MINUTES)).isoformat() + "Z"
    
    availability_data = await check_slot_availability(contact_id, start_time, end_time)
    
    if availability_data.get("success"):
        if availability_data.get("data", {}).get("isAvailable"):
            return AnswerResponse(
                status=True,
                query=query,
                answer=f" Yes,this slot is Available  {parsed_time}!\n\n If you want to book,Then responed like \n\n👉 Example: *I want to Book an appointment for {parsed_time}*."
            )
        else:
            return AnswerResponse(
                status=True,
                query=query,
                answer=f" Slot is already booked,Please select another slots!"
            )

@mcp.tool()
async def handle_slot_cancellation( request, parsed_time):
    """Handle appointment cancellation"""
    
    parsed_time = datetime.fromisoformat(str(parsed_time))

    if not (parsed_time and has_time_info(parsed_time)):
        return AnswerResponse(
            status=True,
            query=request.get("query"),
            answer=(
                "🕒 Please provide the both date and time you want to cancel an appointment.\n\n"

            )
        )

    contact_id = request.get("chat_id")
    start_time = parsed_time.isoformat() + "Z"
    end_time = (parsed_time + timedelta(minutes=config.DEFAULT_APPOINTMENT_DURATION_MINUTES)).isoformat() + "Z"

    canceling_success = await cancel_appointment(contact_id, start_time, end_time)

    if canceling_success:
        return AnswerResponse(
            status=True,
            query=request.get("query"),
            answer=f"✅ Appointment cancelled successfully for {parsed_time}!"
        )
    else:
        return AnswerResponse(

            status=False,
            query=request.get("query"),
            answer="❌ That, slot is already cancelled,Unable to cancel the appointment."
        )

@mcp.tool()
async def handle_date_time_if_not_provided(days):
    """Handle when date/time is not provided in user query"""
    start_time = datetime.now(timezone.utc)
    
    end_time = start_time + timedelta(days=days)
    
    return {"start time": start_time, "end time": end_time}

CONNECTION_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=PropertyDB;"
    "Trusted_Connection=yes;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

conn = pyodbc.connect(CONNECTION_STRING)

@mcp.tool()
async def get_project_details(name):
    """"Processes a project detail-related query by fetching project details from the database.
    args:
        name: The name of the project to query.
    returns:
        The project details in JSON format.
    """
    
    name = name.lower()
    name = name.replace("project", "")
    name = name.replace("property", "")
    with conn.cursor() as cur:
        cur.execute("""
                SELECT * FROM tblProjDetails WHERE ProjectName = ?
            """, (name.strip(),))

        rows = cur.fetchone()

    if rows:
        columns = [column[0] for column in cur.description]
        project_dict = dict(zip(columns, rows))

        return json.dumps(project_dict, indent=4, default=str)
    
    return f"No project found with name {name}"