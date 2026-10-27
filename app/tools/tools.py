from langchain.tools import tool
from typing import Any

from app.agent.memory import memory_service
from app.services.appointment import appointment_services
from app.services.database import query_database, SearchFilters
from app.services.otp import otp_service


@tool
def recall_past_conversations(user_id: str, query: str, top_k: int = 5) -> str:
    """Recall the most relevant earlier conversation turns for one user.

    Use this when the client's message refers to something discussed in an
    earlier chat (a project they asked about, a budget, a preferred area, or a
    previous booking) and that context is not already visible in the current
    conversation. Returns at most ``top_k`` matching turns, oldest first, or a
    short note when nothing relevant is found.

    Args:
        user_id (str): The Chat ID from the latest user message.
        query (str): What the client is asking about now.
        top_k (int): Maximum number of past turns to return (default 5).

    Returns:
        The most relevant past turns as compact text.
    """
    rows = memory_service.long_term.retrieve_relevant(user_id, query, top_k)
    if not rows:
        return "No relevant past conversations found."

    lines = []
    for role, content, _created_at in rows:
        speaker = "Client" if role == "user" else "Assistant"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


@tool()    
async def check_slot_availability(contact_id: str, start_time: str, end_time: str):
    """Check the available slots for requested time.

    Args:
        contact_id (str): contact_id of user.
        start_time (str): starting time of appointment.
        end_time (str): ending time of appointment.
    
    Returns:
        Available appointment slots.
    """
    try:
        response = await appointment_services.check_slot_availability(contact_id, start_time, end_time)
        return response

    except Exception as e:
        return e

@tool()
async def book_appointment(contact_id: str, start_time: str, end_time: str, query: str):
    """Book appointment for requested time.

    Args:
        contact_id (str): contact_id of user.
        start_time (str): starting time of appointment.
        end_time (str): ending time of appointment.
        query (str): user query.

    Returns:
        Appointment booking status.
    """
    try:
        response = await appointment_services.book_appointment(contact_id, start_time, end_time, query)
        return response

    except Exception as e:
        return e

@tool()
async def cancel_appointment(contact_id: str, start_time: str, end_time: str):
    """Check and cancel an existing appointment.

    Args:
        contact_id (str): contact_id of user.
        start_time (str): starting time of appointment.
        end_time (str): ending time of appointment.
    Returns:
        Cancelled appointment status.
    """
    try:
        response = await appointment_services.cancel_appointment(contact_id, start_time, end_time)
        return response

    except Exception as e:
        return e

@tool()
async def reschedule_appointment(contact_id: str, query: str, cancel_time: str, appointment_time: str):
    """
    Reschedule perviously booked appointment.
    
    Args:
        contact_id: str = Contact ID of user, must be secret.
        query: str = Query of the user.
        cancel_time: str = Old appointment time to cancel.
        appointment_time: str = New appointment time to book.
    
    Returns:
        Appointment status (Json).
    """
    try:
        response = await appointment_services.reschedule_appointment(contact_id, query, cancel_time, appointment_time)
        return response
    
    except Exception as e:
        return e

@tool()
async def add_or_update_user_email(contact_id: str, email: str):
    """
    Add or update the Email of the agent if not exists.
    
    Args:
        contact_id: str = Contact ID of user, must be secret.
        email: str = Email of the user.
    
    Returns:
        Email status (Json).
    """
    try:
        response = await appointment_services.add_or_update_user_email(contact_id, email)
        return response

    except Exception as e:
        return e

@tool()
async def handle_date_time_if_not_provided(days: int):
    """
    Handle when date/time is not provided in user query and return date, day, time, year.
    
    Args:
        days: int = Forward days.
    
    Returns:
        Forward days Date, Time, Day, Year.
    """
    try:
        response = await appointment_services.handle_date_time_if_not_provided(days)
        return response

    except Exception as e:
        return e

@tool()
async def check_current_date_time():
    """
    Returns current date, time and day

    Args:
        None
    
    Returns:
        Current Date, Time, Day, Year.
    """
    try:
        response = await appointment_services.check_current_date_time()
        return response

    except Exception as e:
        return e

@tool()
async def get_project_details(question: str, project_name: str | None = None, filters: SearchFilters | None = None,):
    """
    Called by the get_project_details tool. Never raises.

    Pass ``project_name`` when the client named a project, or ``filters`` (see
    SearchFilters) when they described what they want. With neither, the
    question itself is interpreted.

    Result ``status`` is one of: success | ambiguous | not_found | no_results |
    needs_clarification | invalid_filters | error.
    """
    try:
        response = await query_database(question, project_name, filters)
        return response

    except Exception as e:
        return e

@tool()
async def generate_otp(email: str, contact_id: str) -> str:
    """
    Generate and send OTP for the provided contact_id and email.

    Args: 
        email: str = Email of recepient.
        contact_id: str = Contact ID of the user.
    
    Returns:
        Generated OTP.
    """
    try:
        response = await otp_service.generate_otp(email, contact_id)
        return response

    except Exception as e:
        return e

@tool()
async def verify_otp(contact_id: str, otp: str) -> str:
    """
    Verify an OTP and return its status.

    Args: 
        contact_id: str = Contact ID of the user.
        otp: str = Generated OTP.

    Returns:
        "verified"  - OTP successfully verified.
        "pending"   - OTP is incorrect but has not expired.
        "expired"   - OTP has expired.
        "not_found" - No record exists for this contact ID.
    """
    try:
        response = await otp_service.verify_otp(contact_id, otp)
        return response

    except Exception as e:
        return e

ALL_TOOLS = [recall_past_conversations, check_slot_availability, book_appointment, cancel_appointment, reschedule_appointment, add_or_update_user_email, handle_date_time_if_not_provided, check_current_date_time, get_project_details]
