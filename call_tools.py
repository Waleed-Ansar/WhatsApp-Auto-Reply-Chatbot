from langchain.tools import tool
from mcp_client import MCPClient
import os
from typing import Optional, Any


SERVER_PATH = os.path.join(os.path.dirname(__file__), "mcp_server.py")

_client: Optional[MCPClient] = None


def _get_client() -> MCPClient:
    global _client
    if _client is None:
        _client = MCPClient(SERVER_PATH)
    return _client


def _call_tool(name: str, arguments: dict) -> Any:
    try:
        client = _get_client()
        return client.call_tool(name=name, arguments=arguments)
    except Exception:
        return "I'm sorry, I can't do this right now."

# Tool to Check Available Slots
@tool()
async def check_slot_availability(contact_id: str, start_time: str, end_time: str):
    """"Checks the available slots for booking an appointment.
    args:
        contact_id: The contact ID of the user.
        start_time: The start time of the desired appointment.
        end_time: The end time of the desired appointment.
    returns:
        The data for the available slots.
    """
    result = _call_tool(
        name="check_slot_availability",
        arguments={
            "contact_id": contact_id,
            "start_time": start_time,
            "end_time": end_time
        }
    )
    return result if isinstance(result, str) else str(result)
# Tool to Book an Appointment
@tool()
async def handle_direct_booking(request, parsed_time):
    """"Books an appointment for the user.
    args:
        request: The request object containing booking details like chat_id, query.
        parsed_time: The starting time for the appointment.
    returns:
        The data for the booked appointment.
    """
    result = _call_tool(
        name="handle_direct_booking",
        arguments={
            "request": request,
            "parsed_time": parsed_time
        }
    )
    return result if isinstance(result, str) else str(result)
# Tool to Handle User Replying with One of the Suggested Times
@tool()
async def handle_suggested_slot_booking(request, parsed_time):
    """"Handle user replying with one of the suggested times.
    args:
        request: The request object containing booking details like chat_id, query.
        parsed_time: The starting time for the appointment.
    returns:
        The data for the booked slots.
    """
    result = _call_tool(
        name="handle_suggested_slot_booking",
        arguments={
            "request": request,
            "parsed_time": parsed_time
        }
    )
    return result if isinstance(result, str) else str(result)
# Tool to Check Slot Availability for Booking
@tool()
async def handle_slot_availability_check(request, parsed_time):
    """"Handles the slot availability check for booking an appointment.
    args:
        request: The request object containing details like chat_id, query.
        parsed_time: The starting time for the appointment.
    returns:
        The data for the available slots.
    """
    result = _call_tool(
        name="handle_slot_availability_check",
        arguments={
            "request": request,
            "parsed_time": parsed_time
        }
    )
    return result if isinstance(result, str) else str(result)
# Tool to Cancel an Appointment Slot
@tool()
async def handle_slot_cancellation(request, parsed_time):
    """"Handles the appointment cancellation for an booked appointment.
    args:
        request: The request object containing details like chat_id, query.
        parsed_time: The starting time for the appointment.
    returns:
        The data for the cancellation.
    """
    result = _call_tool(
        name="handle_slot_cancellation",
        arguments={
            "request": request,
            "parsed_time": parsed_time
        }
    )
    return result if isinstance(result, str) else str(result)

@tool()
async def add_or_update_user_email(chat_id: str, email: str):
    """Adds or updates user email in the system.
    args:
        chat_id: The chat ID of the user.
        email: The email address of the user to be added.
    returns:
        The data for the added email.
    """
    result = _call_tool(
        name="add_or_update_user_email",
        arguments={
            "chat_id": chat_id,
            "email": email
        }
    )

    return result if isinstance(result, str) else str(result)

@tool()
async def reschedule_appointment(request, cancel_time, appointment_time):
    """"Handles the appointment cancellation for an booked appointment.
    args:
        request: The request object containing details like chat_id, query.
        cancel_time: The cancellation time for old appointment.
        appointment_time: The starting time for new appointment.
    returns:
        The data for the cancellation of old appointment and booking of new appointment.
    """
    result = _call_tool(
        name="reschedule_appointment",
        arguments={
            "request": request,
            "cancel_time": cancel_time,
            "appointment_time": appointment_time
        }
    )
    return result if isinstance(result, str) else str(result)

# Tool to Get Project Details
@tool()
async def get_project_details(query):
    """"Give the details of a real estate project based on asked question.
    args:
        query: The query is asked question about project.
    returns:
        The answer to the project-related query.
    """
    result = _call_tool(
        name="get_project_details",
        arguments={
            "query": query
        }
    )
    return result if isinstance(result, str) else str(result)

@tool()
async def handle_date_time_if_not_provided(days: int):
    """Give the start and end time based on provided days if not provided by user.
    args:
        days: Number of days forward.
    return:
        Start time and End Time.
    """
    result = _call_tool(
        name="handle_date_time_if_not_provided",
        arguments={
            "days": days
        }
    )
    return result if isinstance(result, str) else str(result)

@tool()
async def check_current_date_time():
    """Returns current date, time and day.
    return:
        Returns current date, time and day.
    """
    result = _call_tool(
        name="check_current_date_time",
        arguments=None
    )
    return result if isinstance(result, str) else str(result)