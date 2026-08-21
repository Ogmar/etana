"""Telemetry API routes."""

from django.urls import path

from . import views

urlpatterns = [
    path("flights/", views.flight_list),
    path("flights/<int:flight_id>/", views.flight_detail),
    path("flights/<int:flight_id>/parameters/", views.parameter_names),
    path("flights/<int:flight_id>/series/<str:parameter_name>/", views.telemetry_series),
    path("flights/<int:flight_id>/since/", views.telemetry_since),
    path("flights/<int:flight_id>/track/", views.track),
    path("flights/<int:flight_id>/latest/", views.latest_state),
    path("flights/<int:flight_id>/loss/", views.loss_summary),
    path("flights/<int:flight_id>/events/", views.events),
]
