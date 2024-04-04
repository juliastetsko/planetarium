import os
import uuid

from django.template.defaultfilters import slugify
from rest_framework.pagination import PageNumberPagination


def astronomy_show_image_file_path(instance, filename):
    _, extension = os.path.splitext(filename)
    filename = f"{slugify(instance.title)}-{uuid.uuid4()}{extension}"

    return os.path.join("uploads/astronomy_shows/", filename)


class ReservationPagination(PageNumberPagination):
    page_size = 5
    max_page_size = 100
