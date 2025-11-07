from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_name_confirmation = State()
    waiting_for_contact = State()

class BookingStates(StatesGroup):
    waiting_for_booking_week = State()
    waiting_for_booking_date = State()
    waiting_for_booking_type = State()
    waiting_for_booking_time = State()
    waiting_for_duration = State()
    waiting_for_join_decision = State()

class ViewBookingsStates(StatesGroup):
    waiting_for_filter_week = State()
    waiting_for_filter_date = State()
    waiting_for_filter_type = State()