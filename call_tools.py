from langchain.tools import tool
from mcp_client import MCPClient


SERVER_PATH = "mcp_server.py"

client = MCPClient(SERVER_PATH)

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

    result = client.call_tool(
        name="check_slot_availability",
        arguments={
            "contact_id": contact_id,
            "start_time": start_time,
            "end_time": end_time
        }
    )

    return f"Result: {result}"

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

    result = client.call_tool(
        name="handle_direct_booking",
        arguments={
            "request": request,
            "parsed_time": parsed_time
        }
    )

    return f"Result: {result}"

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

    result = client.call_tool(
        name="handle_suggested_slot_booking",
        arguments={
            "request": request,
            "parsed_time": parsed_time
        }
    )

    return f"Result: {result}"

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

    result = client.call_tool(
        name="handle_slot_availability_check",
        arguments={
            "request": request,
            "parsed_time": parsed_time
        }
    )

    return f"Result: {result}"

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

    result = client.call_tool(
        name="handle_slot_cancellation",
        arguments={
            "request": request,
            "parsed_time": parsed_time
        }
    )

    return f"Result: {result}"

# Tool to Get Project Details
@tool()
async def get_project_details(query: str):
    """"Give the details of a real estate project using provided name.
    args:
        query: The query is project name.
    returns:
        The answer to the project-related query.
    """
    result = client.call_tool(
        name="get_project_details",
        arguments={
            "name": query.upper()
        }
    )

    return f"Result: {result}"

@tool()
async def handle_date_time_if_not_provided(days: int):
    """Give the start and end time based on provided days if not provided by user.
    args:
        days: Number of days forward.
    return:
        Start time and End Time.
    """
    
    result = client.call_tool(
        name="handle_date_time_if_not_provided",
        arguments={
            "days": days
        }
    )

    return f"Result: {result}"