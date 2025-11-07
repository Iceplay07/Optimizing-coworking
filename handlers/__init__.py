from .start import register_start_handlers
from .registration import register_registration_handlers
from .booking import register_booking_handlers
from .common import register_common_handlers
from .profile import register_profile_handlers
from .admin import register_admin_handlers
from .view_bookings import register_view_bookings_handlers

def register_all_handlers(dp):
    register_start_handlers(dp)
    register_registration_handlers(dp)
    register_booking_handlers(dp)
    register_common_handlers(dp)
    register_profile_handlers(dp)
    register_admin_handlers(dp)
    register_view_bookings_handlers(dp)