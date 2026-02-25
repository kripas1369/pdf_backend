from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Book, BookBooking
from .serializers import (
    BookListSerializer,
    BookDetailSerializer,
    BookCreateSerializer,
    BookBookingSerializer,
    MyBookListSerializer,
)
from .permissions import IsOwnerOrReadOnly


class BookListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class BookListView(APIView):
    """GET /api/books/ — List all available books (paginated, filterable)."""
    permission_classes = [AllowAny]
    pagination_class = BookListPagination

    def get(self, request):
        qs = Book.objects.filter(is_available=True, is_approved=True)

        category = request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        min_price = request.query_params.get('min_price')
        if min_price is not None:
            try:
                qs = qs.filter(price__gte=float(min_price))
            except (TypeError, ValueError):
                pass

        max_price = request.query_params.get('max_price')
        if max_price is not None:
            try:
                qs = qs.filter(price__lte=float(max_price))
            except (TypeError, ValueError):
                pass

        sort = request.query_params.get('sort', '')
        if sort == 'price_low':
            qs = qs.order_by('price')
        elif sort == 'price_high':
            qs = qs.order_by('-price')
        else:
            qs = qs.order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = BookListSerializer(
                page, many=True, context={'request': request}
            )
            return paginator.get_paginated_response(serializer.data)
        serializer = BookListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class BookDetailView(APIView):
    """GET /api/books/<id>/ — Book detail; increments views_count."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        book.views_count += 1
        book.save(update_fields=['views_count'])
        serializer = BookDetailSerializer(book, context={'request': request})
        return Response(serializer.data)


class BookCreateView(APIView):
    """POST /api/books/create/ — Upload a new book (auth required, multipart)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        book = serializer.save()
        detail_serializer = BookDetailSerializer(
            book, context={'request': request}
        )
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class BookBookingView(APIView):
    """POST /api/books/<id>/book/ — Book/reserve a book (auth required)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response(
                {'detail': 'Book not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = {
            'book': book.id,
            'buyer_name': request.data.get('buyer_name'),
            'buyer_phone': request.data.get('buyer_phone'),
            'buyer_message': request.data.get('buyer_message', ''),
        }
        serializer = BookBookingSerializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(
            BookBookingSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )


class MyBooksView(APIView):
    """GET /api/books/my-books/ — Current user's listed books (auth required)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Book.objects.filter(seller=request.user).order_by('-created_at')
        serializer = MyBookListSerializer(
            qs, many=True, context={'request': request}
        )
        return Response(serializer.data)


class BookBookingsListView(APIView):
    """GET /api/books/<id>/bookings/ — Bookings for a book (seller only)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response(
                {'detail': 'Book not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if book.seller_id != request.user.id:
            return Response(
                {'detail': 'You can only view bookings for your own books.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = book.bookings.all()
        serializer = BookBookingSerializer(qs, many=True)
        return Response(serializer.data)


class BookUpdateView(APIView):
    """PATCH or PUT /api/books/<id>/update/ — Edit book details (seller only, partial)."""
    permission_classes = [IsAuthenticated]

    def _update(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response(
                {'detail': 'Book not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if book.seller_id != request.user.id:
            return Response(
                {'detail': 'You can only update your own books.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = BookCreateSerializer(
            book,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        detail_serializer = BookDetailSerializer(
            book, context={'request': request}
        )
        return Response(detail_serializer.data)

    def patch(self, request, pk):
        return self._update(request, pk)

    def put(self, request, pk):
        return self._update(request, pk)


class BookDeleteView(APIView):
    """DELETE /api/books/<id>/delete/ — Delete book (seller only)."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response(
                {'detail': 'Book not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if book.seller_id != request.user.id:
            return Response(
                {'detail': 'You can only delete your own books.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        book.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
