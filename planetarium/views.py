from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from planetarium.models import (
    ShowTheme,
    PlanetariumDome,
    AstronomyShow,
    ShowSession,
    Reservation,
)
from planetarium.serializers import (
    ShowThemeSerializer,
    PlanetariumDomeSerializer,
    AstronomyShowSerializer,
    AstronomyShowListSerializer,
    AstronomyShowDetailSerializer,
    AstronomyShowImageSerializer,
    ShowSessionSerializer,
    ShowSessionListSerializer,
    ShowSessionDetailSerializer,
    ReservationSerializer,
    ReservationListSerializer,
)
from planetarium.utils import ReservationPagination


class ShowThemeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = ShowTheme.objects.all()
    serializer_class = ShowThemeSerializer


class PlanetariumDomeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = PlanetariumDome.objects.all()
    serializer_class = PlanetariumDomeSerializer


class AstronomyShowViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = AstronomyShow.objects.prefetch_related("show_themes")
    serializer_class = AstronomyShowSerializer

    @staticmethod
    def _params_to_strs(qs):
        """Converts a list of string to a list of strings"""
        return [param.strip() for param in qs.split(",")]

    def get_queryset(self):
        """Retrieve the astronomy show with filters"""
        title = self.request.query_params.get("title")
        show_themes = self.request.query_params.get("show_themes")

        queryset = self.queryset

        if title:
            queryset = queryset.filter(title__icontains=title)

        if show_themes:
            show_theme_names = self._params_to_strs(show_themes)
            queryset = queryset.filter(show_themes__name__in=show_theme_names)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return AstronomyShowListSerializer

        if self.action == "retrieve":
            return AstronomyShowDetailSerializer

        if self.action == "upload_image":
            return AstronomyShowImageSerializer

        return self.serializer_class

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        astronomy_show = self.get_object()
        serializer = self.get_serializer(astronomy_show, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "title",
                type=str,
                description="Filter by title",
            ),
            OpenApiParameter(
                "show_themes", type=str, description="Filter by show_themes"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ShowSessionViewSet(viewsets.ModelViewSet):
    queryset = (
        ShowSession.objects
        .select_related("astronomy_show", "planetarium_dome")
        .annotate(
            tickets_available=(F("planetarium_dome__rows")
                               * F("planetarium_dome__seats_in_row")
                               - Count("tickets")
                               )
        )
    )
    serializer_class = ShowSessionSerializer

    def get_queryset(self):
        date = self.request.query_params.get("date")
        astronomy_show_id_str = self.request.query_params.get("astronomy_show")

        queryset = super().get_queryset()

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        if astronomy_show_id_str:
            queryset = queryset.filter(
                astronomy_show_id=int(astronomy_show_id_str)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ShowSessionListSerializer

        if self.action == "retrieve":
            return ShowSessionDetailSerializer

        return self.serializer_class

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description="Filter by date",
            ),
            OpenApiParameter(
                "astronomy_show_",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by astronomy show id",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ReservationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    queryset = Reservation.objects.prefetch_related(
        "tickets__show_session__astronomy_show",
        "tickets__show_session__planetarium_dome",
    )
    serializer_class = ReservationSerializer
    pagination_class = ReservationPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return ReservationListSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
