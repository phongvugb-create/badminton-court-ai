"""Structured UI destinations built from server-side facility records."""


def booking_actions(facility_id, name, date=None):
    return [
        {'type': 'open_booking', 'facility_id': int(facility_id), 'date': date,
         'section': section, 'label': f'{label} — {name}'}
        for section, label in [('schedule', 'Mở lịch đặt sân'), ('equipment', 'Thuê thiết bị kèm sân')]
    ]
