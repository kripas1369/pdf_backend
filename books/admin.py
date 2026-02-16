from django.contrib import admin
from django.utils.html import format_html
from .models import Book, BookBooking


class BookBookingInline(admin.TabularInline):
    model = BookBooking
    extra = 0
    readonly_fields = ('book', 'buyer', 'buyer_name', 'buyer_phone', 'buyer_message', 'status', 'created_at')
    can_delete = True
    show_change_link = True


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'seller_link', 'price', 'category', 'condition',
        'location', 'is_available', 'is_approved', 'views_count',
        'total_bookings_display', 'created_at',
    )
    list_filter = ('is_available', 'is_approved', 'category', 'condition', 'created_at')
    search_fields = ('title', 'description', 'seller__name', 'seller__phone', 'location')
    readonly_fields = ('seller', 'views_count', 'created_at', 'updated_at')
    inlines = [BookBookingInline]

    def seller_link(self, obj):
        name = getattr(obj.seller, 'name', None) or obj.seller.phone or '—'
        phone = getattr(obj.seller, 'phone', '')
        return format_html('{} ({})', name, phone)
    seller_link.short_description = 'Seller'
    seller_link.admin_order_field = 'seller__name'

    def total_bookings_display(self, obj):
        return obj.bookings.count()
    total_bookings_display.short_description = 'Total bookings'

    actions = ['approve_books', 'reject_books', 'mark_as_sold']

    def save_model(self, request, obj, form, change):
        if not change and not obj.seller_id:
            obj.seller = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Approve selected books')
    def approve_books(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} book(s) approved.')

    @admin.action(description='Reject selected books')
    def reject_books(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} book(s) rejected.')

    @admin.action(description='Mark as sold')
    def mark_as_sold(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} book(s) marked as sold.')


@admin.register(BookBooking)
class BookBookingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'book_title_display', 'seller_info_display',
        'buyer_name', 'buyer_phone', 'buyer_message_short', 'status', 'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('book__title', 'buyer_name', 'buyer_phone', 'buyer__name')

    def book_title_display(self, obj):
        return obj.book.title
    book_title_display.short_description = 'Book'
    book_title_display.admin_order_field = 'book__title'

    def seller_info_display(self, obj):
        s = obj.book.seller
        name = getattr(s, 'name', None) or s.phone or '—'
        phone = getattr(s, 'phone', '')
        return format_html('{} ({})', name, phone)
    seller_info_display.short_description = 'Seller'
    seller_info_display.admin_order_field = 'book__seller__name'

    def buyer_message_short(self, obj):
        if not obj.buyer_message:
            return '—'
        return obj.buyer_message[:50] + '…' if len(obj.buyer_message) > 50 else obj.buyer_message
    buyer_message_short.short_description = 'Message'

    actions = ['accept_booking', 'reject_booking']

    @admin.action(description='Accept selected bookings')
    def accept_booking(self, request, queryset):
        updated = queryset.update(status='ACCEPTED')
        self.message_user(request, f'{updated} booking(s) accepted.')

    @admin.action(description='Reject selected bookings')
    def reject_booking(self, request, queryset):
        updated = queryset.update(status='REJECTED')
        self.message_user(request, f'{updated} booking(s) rejected.')
