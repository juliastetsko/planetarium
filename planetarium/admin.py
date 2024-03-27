from django.contrib import admin

from planetarium.models import (
    Reservation,
    PlanetariumDome,
    ShowTheme,
    AstronomyShow,
    ShowSession,
    Ticket,
)

admin.site.register(Reservation)
admin.site.register(PlanetariumDome)
admin.site.register(ShowTheme)
admin.site.register(AstronomyShow)
admin.site.register(ShowSession)
admin.site.register(Ticket)
