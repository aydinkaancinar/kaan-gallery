from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from .models import Item, Artist, ArtworkImage
from .serializers import ItemSerializer, ItemFilterSerializer, ArtistSerializer, PublicItemSerializer
from django.db.models import F, Q
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import permission_classes
from django.http import FileResponse, Http404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .permissions import IsAdminOrReadOnly, is_verified_staff
import re
from rest_framework.exceptions import PermissionDenied

def artwork_read_serializer(user):
    if is_verified_staff(user):
        return ItemSerializer

    return PublicItemSerializer


def visible_artists(user):
    artists = Artist.objects.all()

    if not is_verified_staff(user):
        artists = artists.filter(
            items__status=Item.Status.PUBLISHED
        ).distinct()

    return artists

@api_view(["GET", "POST"])
@permission_classes([IsAdminOrReadOnly])
def getData(request):
    if request.method == "GET":
        verified_staff = is_verified_staff(request.user)
        if not verified_staff:
            uses_price_filter = any(
                key in request.query_params for key in ("min_price", "max_price")
            )
            # Check every supplied sort value, including duplicate parameters.
            uses_price_sort = Item.Fields.PRICE in request.query_params.getlist("order_by")
            if uses_price_filter or uses_price_sort:
                raise PermissionDenied(
                    "Price filters and sorting require verified staff."
                )

        filters = ItemFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)

        items = Item.objects.select_related("artist").prefetch_related("tags", "images")
        if not verified_staff:
            items = items.filter(status=Item.Status.PUBLISHED)

        minimum = filters.validated_data.get("min_price")
        maximum = filters.validated_data.get("max_price")
        category = filters.validated_data.get("category")
        name = filters.validated_data.get("name")
        order_by = filters.validated_data.get("order_by")
        search = filters.validated_data.get("search")
        artist = filters.validated_data.get("artist")
        tag = filters.validated_data.get("tag")
        creation_year = filters.validated_data.get("creation_year")
        creation_month = filters.validated_data.get("creation_month")
        created_from = filters.validated_data.get("created_from")
        created_to = filters.validated_data.get("created_to")

        if creation_year is not None:
            items = items.filter(creation_year=creation_year)

        if creation_month is not None:
            items = items.filter(creation_month=creation_month)

        if created_from is not None:
            year, month = map(int, created_from.split("-"))

            items = items.filter(
                Q(creation_year__gt=year)
                | Q(creation_year=year, creation_month__gte=month)
            )

        if created_to is not None:
            year, month = map(int, created_to.split("-"))

            items = items.filter(
                Q(creation_year__lt=year)
                | Q(creation_year=year, creation_month__lte=month)
            )

        if minimum is not None:
            items = items.filter(price__gte=minimum)

        if maximum is not None:
            items = items.filter(price__lte=maximum)

        if category is not None:
            items = items.filter(category=category)

        if name is not None:
            items = items.filter(name__icontains=name)

        if artist is not None:
            items = items.filter(artist__name__icontains=artist)

        if tag is not None:
            tag_query = Q()

            for tag_name in tag:
                tag_query |= Q(tags__name__iexact=tag_name)

            items = items.filter(tag_query).distinct()

        if order_by is not None:
            if order_by == Item.Fields.PRICE:
                items = items.order_by("price", "name", "category", "id")
            elif order_by == Item.Fields.NAME:
                items = items.order_by("name", "price", "category", "id")
            elif order_by == Item.Fields.CATEGORY:
                items = items.order_by("category", "name", "price", "id")
            elif order_by == Item.Fields.CREATED:
                items = items.order_by("created", "category", "name", "price", "id")
            elif order_by == Item.Fields.CREATION_DATE_ASCENDING:
                items = items.order_by(
                    F("creation_year").asc(nulls_last=True),
                    F("creation_month").asc(nulls_last=True),
                    "name",
                    "id",
                )
            elif order_by == Item.Fields.CREATION_DATE_DESCENDING:
                items = items.order_by(
                    F("creation_year").desc(nulls_last=True),
                    F("creation_month").desc(nulls_last=True),
                    "name",
                    "id",
                )
        else:
            items = items.order_by(*Item._meta.ordering)

        if not is_verified_staff(request.user):
            if order_by == Item.Fields.NAME:
                items = items.order_by("name", "category", "id")
            elif order_by == Item.Fields.CATEGORY:
                items = items.order_by("category", "name", "id")
            elif order_by == Item.Fields.CREATED:
                items = items.order_by("created", "category", "name", "id")

        if search is not None:
            term = search.strip()

            if re.fullmatch(r"[0-9]{4}", term):
                items = items.filter(creation_year=int(term))

            elif re.fullmatch(r"[0-9]{4}-[0-9]{2}", term):
                year, month = map(int, term.split("-"))

                items = items.filter(
                    creation_year=year,
                    creation_month=month,
                )

            else:
                items = items.filter(
                    Q(name__icontains=term)
                    | Q(description__icontains=term)
                )
                        
        paginator = PageNumberPagination()

        page = paginator.paginate_queryset(items, request)

        serializer_class = artwork_read_serializer(request.user)
        serializer = serializer_class(
            page,
            many=True,
            context={
                "include_artist": filters.validated_data.get("include_artist", False),
            },
        )

        return paginator.get_paginated_response(serializer.data)
    
    if request.method == "POST":
        serializer = ItemSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response(serializer.data, status=201)


@api_view(["DELETE","PATCH","GET"])
@permission_classes([IsAdminOrReadOnly])
def operateItem(request, item_id):
    items = Item.objects.select_related("artist").prefetch_related("tags", "images")
    if not is_verified_staff(request.user):
        items = items.filter(status=Item.Status.PUBLISHED)
    item = get_object_or_404(items, pk=item_id)
    if request.method == "DELETE":
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    if request.method == "GET":
        serializer_class = artwork_read_serializer(request.user)
        serializer = serializer_class(item)
        return Response(serializer.data, status=status.HTTP_200_OK)
    if request.method == "PATCH":
        serializer = ItemSerializer(
            instance=item,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)

@api_view(["GET", "POST"])
@permission_classes([IsAdminOrReadOnly])
def artistAPI(request):
    if request.method == "GET":
        artists = visible_artists(request.user)
        serializer = ArtistSerializer(artists, many=True)
        return Response(serializer.data)
    
    if request.method == "POST":
        serializer = ArtistSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response(serializer.data, status=201)

@api_view(["DELETE","PATCH","GET"])
@permission_classes([IsAdminOrReadOnly])
def operateArtist(request, item_id):
    artist = get_object_or_404(
        visible_artists(request.user),
        pk=item_id,
    )
    if request.method == "DELETE":
        artist.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    if request.method == "GET":
        serializer = ArtistSerializer(artist)
        return Response(serializer.data, status=status.HTTP_200_OK)
    if request.method == "PATCH":
        serializer = ArtistSerializer(
            instance=artist,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAdminOrReadOnly])
def artwork_detail(request, slug):
    items = Item.objects.select_related("artist").prefetch_related("tags", "images")

    if not is_verified_staff(request.user):
        items = items.filter(status=Item.Status.PUBLISHED)

    item = get_object_or_404(items, slug=slug)
    serializer_class = artwork_read_serializer(request.user)
    serializer = serializer_class(item)

    return Response(serializer.data)

@never_cache
@require_GET
def artwork_image(request, image_id):
    images = ArtworkImage.objects.select_related("item")

    if not is_verified_staff(request.user):
        images = images.filter(item__status=Item.Status.PUBLISHED)

    artwork_image = get_object_or_404(images, pk=image_id)

    if not artwork_image.image:
        raise Http404("Image not found.")

    try:
        file = artwork_image.image.open("rb")
    except FileNotFoundError:
        raise Http404("Image not found.")

    response = FileResponse(file)
    response["X-Content-Type-Options"] = "nosniff"
    return response

@api_view(["GET"])
@permission_classes([IsAdminOrReadOnly])
def artwork_date_bounds(request):
    dated_artworks = Item.objects.filter(
        status=Item.Status.PUBLISHED,
        creation_year__isnull=False,
        creation_month__isnull=False,
    )

    earliest = dated_artworks.order_by(
        "creation_year", "creation_month", "id"
    ).values_list("creation_year", "creation_month").first()

    latest = dated_artworks.order_by(
        "-creation_year", "-creation_month", "-id"
    ).values_list("creation_year", "creation_month").first()

    def format_month(value):
        if value is None:
            return None

        year, month = value
        return f"{year:04d}-{month:02d}"

    return Response({
        "earliest": format_month(earliest),
        "latest": format_month(latest),
    })


@api_view(["GET"])
@permission_classes([IsAdminOrReadOnly])
def artwork_categories(request):
    """Public catalog categories, independent of filters and pagination."""
    populated = set(
        Item.objects.filter(status=Item.Status.PUBLISHED)
        .order_by()
        .values_list("category", flat=True)
        .distinct()
    )
    return Response([
        {"value": value, "label": label}
        for value, label in Item.Category.choices
        if value in populated
    ])
