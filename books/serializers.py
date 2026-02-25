from rest_framework import serializers
from .models import Book, BookBooking
from .utils import compress_image


def _seller_name(obj):
    return getattr(obj.seller, 'name', None) or getattr(obj.seller, 'phone', '')


def _seller_phone(obj):
    return getattr(obj.seller, 'phone', '')


def _front_image_url(request, obj):
    if obj.front_image:
        return request.build_absolute_uri(obj.front_image.url)
    return None


class BookListSerializer(serializers.ModelSerializer):
    seller_name = serializers.SerializerMethodField()
    seller_phone = serializers.SerializerMethodField()
    front_image = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'price', 'location', 'front_image',
            'condition', 'category', 'seller_name', 'seller_phone',
            'is_available', 'views_count', 'created_at',
        ]

    def get_seller_name(self, obj):
        return _seller_name(obj)

    def get_seller_phone(self, obj):
        return _seller_phone(obj)

    def get_front_image(self, obj):
        request = self.context.get('request')
        if request:
            return _front_image_url(request, obj)
        return obj.front_image.url if obj.front_image else None


class BookDetailSerializer(serializers.ModelSerializer):
    seller_name = serializers.SerializerMethodField()
    seller_phone = serializers.SerializerMethodField()
    front_image = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    total_bookings = serializers.SerializerMethodField()
    has_booked = serializers.SerializerMethodField()
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'description', 'price', 'location', 'contact_number',
            'front_image', 'condition', 'condition_display', 'category', 'category_display',
            'seller_name', 'seller_phone', 'is_available', 'is_owner', 'total_bookings',
            'has_booked', 'views_count', 'created_at',
        ]

    def get_seller_name(self, obj):
        return _seller_name(obj)

    def get_seller_phone(self, obj):
        return _seller_phone(obj)

    def get_front_image(self, obj):
        request = self.context.get('request')
        if request:
            return _front_image_url(request, obj)
        return obj.front_image.url if obj.front_image else None

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user == obj.seller
        return False

    def get_total_bookings(self, obj):
        return obj.bookings.count()

    def get_has_booked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookings.filter(buyer=request.user).exists()
        return False


class MyBookListSerializer(BookListSerializer):
    """List serializer for my-books: same as list + total_bookings."""
    total_bookings = serializers.SerializerMethodField()

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + ['total_bookings']

    def get_total_bookings(self, obj):
        return obj.bookings.count()


class BookCreateSerializer(serializers.ModelSerializer):
    ALLOWED_IMAGE_FORMATS = ('jpg', 'jpeg', 'png', 'webp')
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

    class Meta:
        model = Book
        fields = [
            'title', 'description', 'price', 'location', 'contact_number',
            'front_image', 'category', 'condition',
        ]

    def validate_price(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Price must be greater than 0.')
        return value

    def validate_front_image(self, value):
        # On create, front_image is required. On update (partial), omit or send empty to keep existing.
        if not value:
            if self.instance is None:
                raise serializers.ValidationError('Front image is required.')
            return getattr(self.instance, 'front_image', None)
        if value.size > self.MAX_IMAGE_SIZE:
            raise serializers.ValidationError('Image size must not exceed 5MB.')
        ext = value.name.split('.')[-1].lower() if value.name else ''
        if ext not in self.ALLOWED_IMAGE_FORMATS:
            raise serializers.ValidationError(
                f'Invalid image format. Allowed: {", ".join(self.ALLOWED_IMAGE_FORMATS)}'
            )
        return value

    def _compress_front_image_if_present(self, validated_data):
        """Compress front_image (e.g. from iPhone) to reduce size before save."""
        if 'front_image' in validated_data and validated_data['front_image']:
            validated_data['front_image'] = compress_image(validated_data['front_image'])

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Authentication required.')
        self._compress_front_image_if_present(validated_data)
        validated_data['seller'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._compress_front_image_if_present(validated_data)
        return super().update(instance, validated_data)


class BookBookingSerializer(serializers.ModelSerializer):
    book_title = serializers.SerializerMethodField()

    class Meta:
        model = BookBooking
        fields = [
            'id', 'book', 'book_title', 'buyer_name', 'buyer_phone',
            'buyer_message', 'status', 'created_at',
        ]
        read_only_fields = ['status']

    def get_book_title(self, obj):
        return obj.book.title

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Authentication required.')
        book = validated_data.get('book')
        if book.seller_id == request.user.id:
            raise serializers.ValidationError({'book': 'Cannot book your own book.'})
        if not book.is_available:
            raise serializers.ValidationError({'book': 'This book is no longer available.'})
        if BookBooking.objects.filter(book=book, buyer=request.user).exists():
            raise serializers.ValidationError({'book': 'You have already booked this book.'})
        validated_data['buyer'] = request.user
        return super().create(validated_data)
