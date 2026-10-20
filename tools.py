import call_tools as ct


ALL_TOOLS = [
    ct.check_slot_availability,
    ct.handle_direct_booking,
    ct.handle_slot_cancellation,
    ct.reschedule_appointment,
    ct.add_or_update_user_email,
    ct.get_project_details,
    ct.handle_date_time_if_not_provided,
    ct.check_current_date_time
]