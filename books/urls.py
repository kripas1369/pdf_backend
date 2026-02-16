from django.urls import path
from . import views

urlpatterns = [
    path('books/', views.BookListView.as_view(), name='book-list'),
    path('books/create/', views.BookCreateView.as_view(), name='book-create'),
    path('books/my-books/', views.MyBooksView.as_view(), name='my-books'),
    path('books/<int:pk>/', views.BookDetailView.as_view(), name='book-detail'),
    path('books/<int:pk>/book/', views.BookBookingView.as_view(), name='book-booking'),
    path('books/<int:pk>/bookings/', views.BookBookingsListView.as_view(), name='book-bookings'),
    path('books/<int:pk>/update/', views.BookUpdateView.as_view(), name='book-update'),
    path('books/<int:pk>/delete/', views.BookDeleteView.as_view(), name='book-delete'),
]
