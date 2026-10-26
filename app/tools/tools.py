from langchain.tools import tool

from app.services.appointment import appointment_services
from app.services.database import query_database
from app.services.otp import otp_service


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
async def check_cancel_appointment(contact_id: str, start_time: str, end_time: str):
    """Check and cancel an existing appointment.

    Args:
        contact_id (str): contact_id of user.
        start_time (str): starting time of appointment.
        end_time (str): ending time of appointment.
    Returns:
        Cancelled appointment status.
    """
    try:
        response = await appointment_services.check_cancel_appointment(contact_id, start_time, end_time)
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
async def get_project_details(query: str):
    """
    Get project details based on the provided query by querying the database.

    Args:
        query: str = Query of the user.

    Returns:
        Requested project details.
    """
    try:
        response = await query_database(query)
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

ALL_TOOLS = [check_slot_availability, book_appointment, check_cancel_appointment, reschedule_appointment, add_or_update_user_email, handle_date_time_if_not_provided, check_current_date_time, get_project_details, generate_otp, verify_otp]