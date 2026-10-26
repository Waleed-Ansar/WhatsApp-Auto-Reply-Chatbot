import httpx
from datetime import timedelta, timezone, datetime

from app.core.config import config
from app.core.datetime_utils import has_time_info
from app.agent.memory import memory_service
from app.schemas.models import AnswerResponse
from app.core.session import get_jwt_token


class AppointmentServices: 
    def __init__(self):
        self.api_base_url = config.API_BASE_URL

    async def check_slot_availability(self, contact_id, start_time: str, end_time: str):
        """
        Check availavle slots for given time.
        
        Args:
            contact_id: str = Contact ID of user, must be secret.
            start_time: str = Appointment starting time.
            end_time: str = Appointment ending time.
        
        Returns:
            Available slots (Json).
        """
        token_expiry, token = await get_jwt_token()
        time_now = datetime.now().astimezone()

        if time_now > token_expiry:
            token_expiry, token = await get_jwt_token()
        
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
                f"{self.api_base_url}/api/GoogleCalendar/CheckSlotAvailability",
                params=params,
                headers=headers
            )
            return response.json()

    async def book_appointment(self, contact_id: str, start_time: str, end_time: str, query: str):
        """
        Book Appointment on given time.
                
        Args:
            contact_id: str = Contact ID of user, must be secret.
            start_time: str = Appointment starting time.
            end_time: str = Appointment ending time.
            query: str = Query of the user.
        
        Returns:
            Status of booked appointment (Json).
        """
        token_expiry, token = await get_jwt_token()
        time_now = datetime.now().astimezone()

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
                f"{self.api_base_url}/api/GoogleCalendar/BookAppointment",
                json=booking_payload,
                headers=headers
            )
            return response.json()



    async def check_cancel_appointment(self, contact_id: str, start_time: str, end_time: str):
        """
        Cancel Appointment of given time.
                
        Args:
            contact_id: str = Contact ID of user, must be secret.
            start_time: str = Appointment starting time.
            end_time: str = Appointment ending time.
        
        Returns:
            Cancellation status (Json).
        """
        token_expiry, token = await get_jwt_token()
        time_now = datetime.now().astimezone()

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
                f"{self.api_base_url}/api/GoogleCalendar/CancelAppointmentAsync",
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

    async def cancel_appointment(self, contact_id: str, start_time: str, end_time: str):
        """
        Cancel Appointment of given time.
                        
        Args:
            contact_id: str = Contact ID of user, must be secret.
            start_time: str = Appointment starting time.
            end_time: str = Appointment ending time.
        
        Returns:
            Cancellation status (Json).
        """
        token_expiry, token = await get_jwt_token()
        time_now = datetime.now().astimezone()

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
                f"{self.api_base_url}/api/GoogleCalendar/CancelAppointmentAsync",
                params=params,
                headers=headers
            )

            print("Status:", response.status_code)
            print("Response:", response.text)

            if response.status_code == 200:
                result = response.json()
                return result.get("success", False)
            return {False,response}



    async def handle_suggested_slot_booking(self, contact_id: str, query: str, parsed_time: datetime):
        """
        Handles slot booking when suggested by user.
        
        Args:
            contact_id: str = Contact ID of user, must be secret.
            start_time: str = Appointment starting time.
            end_time: str = Appointment ending time.
        
        Returns:
            Appointment status (Json).
        """
        suggestions = memory_service.get_user_slot_suggestions(contact_id)
        parsed_time = datetime.fromisoformat(str(parsed_time))
        
        if suggestions and parsed_time:
            for start, end in suggestions:
                if abs((parsed_time - start).total_seconds()) < config.SLOT_TOLERANCE_SECONDS:
                    booking_response = await self.book_appointment(
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

    async def handle_direct_booking(self, contact_id: str, query: str, parsed_time: datetime):
        """
        Handle direct appointment booking.
        
        Args:
            contact_id: str = Contact ID of user, must be secret.
            start_time: str = Appointment starting time.
            end_time: str = Appointment ending time.
        
        Returns:
            Appointment booking status (Json).
        """
        parsed_time = datetime.fromisoformat(str(parsed_time))

        if not (parsed_time and has_time_info(parsed_time)):
            return AnswerResponse(
                status=True,
                query=query,
                answer=(
                    "🕒 Please provide the both date and time you want to book an appointment.\n\n"

                )
            )

        start_time = parsed_time.isoformat() + "Z"
        end_time = (parsed_time + timedelta(minutes=config.DEFAULT_APPOINTMENT_DURATION_MINUTES)).isoformat() + "Z"
        
        availability_data = await self.check_slot_availability(contact_id, start_time, end_time)
        
        if availability_data.get("success"):
            if availability_data.get("data", {}).get("isAvailable"):
                booking_response = await self.book_appointment(contact_id, start_time, end_time, query)
                
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
                        answer=f"❌ Failed to book appointment. Message: {booking_response.get('message', 'No message')}"
                    )
            else:
                return await self.handle_unavailable_slot(contact_id, query, availability_data)
        else:
            return AnswerResponse(
                status=True,
                query=query,
                answer=availability_data.get("message")
            )

    async def handle_unavailable_slot(self, contact_id: str, query: str, availability_data):
        """Handle when requested slot is unavailable"""
        availability = availability_data.get("data", {})
        suggestions = availability.get("suggestions", [])
        
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

    async def handle_slot_availability_check(self, contact_id: str, query: str, parsed_time: datetime):
        """Handle slot availability checking"""
        parsed_time = datetime.fromisoformat(str(parsed_time))

        if not (parsed_time and has_time_info(parsed_time)):
            return AnswerResponse(
                status=True,
                query=query,
                answer=(
                    "🕒 Please provide the both date and time you want check the slots availability.\n\n"

                )
            )

        start_time = parsed_time.isoformat() + "Z"
        end_time = (parsed_time + timedelta(minutes=config.DEFAULT_APPOINTMENT_DURATION_MINUTES)).isoformat() + "Z"
        
        availability_data = await self.check_slot_availability(contact_id, start_time, end_time)
        
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

    async def handle_slot_cancellation(self, contact_id: str, query: str, parsed_time):
        """Handle appointment cancellation"""
        
        parsed_time = datetime.fromisoformat(str(parsed_time))

        if not (parsed_time and has_time_info(parsed_time)):
            return AnswerResponse(
                status=True,
                query=query,
                answer=(
                    "🕒 Please provide the both date and time you want to cancel an appointment.\n\n"

                )
            )

        start_time = parsed_time.isoformat() + "Z"
        end_time = (parsed_time + timedelta(minutes=config.DEFAULT_APPOINTMENT_DURATION_MINUTES)).isoformat() + "Z"

        canceling_success = await self.cancel_appointment(contact_id, start_time, end_time)

        if canceling_success:
            return AnswerResponse(
                status=True,
                query=query,
                answer=f"✅ Appointment cancelled successfully for {parsed_time}!"
            )
        else:
            return AnswerResponse(

                status=False,
                query=query,
                answer="❌ That, slot is already cancelled,Unable to cancel the appointment."
            )

    async def reschedule_appointment(self, contact_id: str, query: str, cancel_time: str, appointment_time: str):
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
            parsed_time = datetime.fromisoformat(str(appointment_time))
            start_time = parsed_time.isoformat() + "Z"
            end_time = (
                parsed_time + timedelta(minutes=config.DEFAULT_APPOINTMENT_DURATION_MINUTES)
            ).isoformat() + "Z"

            availability_data = await self.check_slot_availability(contact_id, start_time, end_time)

            if not availability_data or availability_data.get("success") != True:
                return AnswerResponse(
                    status=False,
                    query=query,
                    answer=f"❌ Failed to check availability. {availability_data.get('message') if isinstance(availability_data, dict) else ''}"
                )

            if not availability_data.get("data", {}).get("isAvailable"):
                return AnswerResponse(
                    status=False,
                    query=query,
                    answer=f"❌ Slot not available for {appointment_time}. Please choose another time. Suggested Slots: {availability_data.get("data").get("suggestions")}"
                )

            cancellation_status = await self.handle_slot_cancellation(contact_id, query, cancel_time)

            if not cancellation_status or cancellation_status.status != True:
                return AnswerResponse(
                    status=False,
                    query=query,
                    answer="❌ Failed to cancel existing appointment."
                )

            booking_response = await self.handle_direct_booking(contact_id, query, appointment_time)

            if not booking_response or booking_response.status != True:
                return AnswerResponse(
                    status=False,
                    query=query,
                    answer="⚠️ Previous appointment cancelled, but failed to book new appointment."
                )

            return AnswerResponse(
                status=True,
                query=query,
                answer=f"✅ Your appointment has been successfully rescheduled to {appointment_time}."
            )

        except Exception as e:
            return AnswerResponse(
                status=False,
                query=query,
                answer=f"❌ Error while rescheduling: {str(e)}"
            )

    async def add_or_update_user_email(self, contact_id: str, email: str):
        """
        Add or update the Email of the agent if not exists.
        
        Args:
            contact_id: str = Contact ID of user, must be secret.
            email: str = Email of the user.
        
        Returns:
            Email status (Json).
        """
        token_expiry, token = await get_jwt_token()
        time_now = datetime.now().astimezone()

        if time_now > token_expiry:
            token_expiry, token = await get_jwt_token()
        
        headers = {
            "Authorization": f"Bearer {token}"
        }

        payload = {
            "contactId": contact_id,
            "email": email
        }

        async with httpx.AsyncClient() as client:
            email_response = await client.request(
                "PATCH",
                f"{self.api_base_url}/api/Contact/UpdateContactEmail",
                json=payload,
                headers=headers
            )
        
        email_response = email_response.json()
        
        if email_response.get("success") == True:
            return AnswerResponse(
                status=True,
                query="Update Email",
                answer=f"✅ Your email has been successfully updated."
            )
        
        else:
            return AnswerResponse(
                status=False,
                query="Update Email",
                answer=f"❌ Failed to update email."
            )

    async def handle_date_time_if_not_provided(self, days: int):
        """
        Handle when date/time is not provided in user query and return date, day, time, year.
        
        Args:
            days: int = Forward days.
        
        Returns:
            Forward days Date, Time, Day, Year.
        """
        
        start_time = datetime.now().astimezone()
        end_time = start_time + timedelta(days=days)
        
        def extract_components(dt):
            return {
                "date": dt.date().isoformat(),       # YYYY-MM-DD
                "day": dt.strftime("%A"),            # Weekday name, e.g., Monday
                "time": dt.strftime("%H:%M:%S"),     # HH:MM:SS
                "year": dt.year
            }
        
        return {
            "start_time": extract_components(start_time),
            "end_time": extract_components(end_time)
        }

    async def check_current_date_time(self):
        """
        Returns current date, time and day

        Args:
            None
        
        Returns:
            Current Date, Time, Day, Year.
        """
        now = datetime.now()

        return {
            "Year": now.year,
            "Month": now.month,
            "Date": now.day,
            
            "Hour": now.hour,
            "Minute": now.minute,
            "Second": now.second,

            "Day": now.strftime("%A")
        }

appointment_services = AppointmentServices()