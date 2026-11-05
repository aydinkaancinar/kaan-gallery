from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from .models import Item, Artist, ArtworkImage
from .serializers import ItemSerializer, ItemFilterSerializer, ArtistSerializer
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import permission_classes
from .permissions import IsAdminOrReadOnly
from django.http import FileResponse, Http404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

@api_view(["GET", "POST"])
@permission_classes([IsAdminOrReadOnly])
def getData(request):
    if request.method == "GET":
        filters = ItemFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)

        items = Item.objects.select_related("artist").prefetch_related("tags", "images")

        if not request.user.is_staff:
            items = items.filter(status=Item.Status.PUBLISHED)
        minimum = filters.validated_data.get("min_price")
        maximum = filters.validated_data.get("max_price")
        category = filters.validated_data.get("category")
        name = filters.validated_data.get("name")
        order_by = filters.validated_data.get("order_by")
        search = filters.validated_data.get("search")
        artist = filters.validated_data.get("artist")
        tag = filters.validated_data.get("tag")

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
        else:
            items = items.order_by("id")

        if search is not None:
            items = items.filter(
                Q(name__icontains=search.strip().lower())
                | Q(description__icontains=search.strip().lower())
            )
                        
        paginator = PageNumberPagination()
        paginator.page_size = 5

        page = paginator.paginate_queryset(items, request)

        serializer = ItemSerializer(
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
    items = Item.objects.all()
    if not request.user.is_staff:
        items = items.filter(status=Item.Status.PUBLISHED)
    item = get_object_or_404(items, pk=item_id)
    if request.method == "DELETE":
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    if request.method == "GET":
        serializer = ItemSerializer(item)
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
        artists = Artist.objects.all()
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
    artist = get_object_or_404(Artist, pk=item_id)
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
    items = Item.objects.select_related("artist").prefetch_related("tags")

    if not request.user.is_staff:
        items = items.filter(status=Item.Status.PUBLISHED)

    item = get_object_or_404(items, slug=slug)
    serializer = ItemSerializer(item)

    return Response(serializer.data)

@never_cache
@require_GET
def artwork_image(request, image_id):
    images = ArtworkImage.objects.select_related("item")
    user = request.user

    verified_staff = (
        user.is_authenticated
        and user.is_active
        and user.is_staff
        and user.is_verified()
    )

    if not verified_staff:
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
