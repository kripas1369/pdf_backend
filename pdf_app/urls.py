from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FeedbackCreateView,
    FeedbackListView,
    TopicViewSet,
    SubjectByTopicView,
    YearListBySubjectView,
    PDFsBySubjectAndYearView
)

router = DefaultRouter()
router.register(r'topics', TopicViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Get subjects for a specific topic
    path('topics/<int:topic_id>/subjects/', SubjectByTopicView.as_view(), name='subjects-by-topic'),
    # Get available years for a specific subject
    path('subjects/<int:subject_id>/years/', YearListBySubjectView.as_view(), name='years-by-subject'),
    # Get PDFs for a specific subject and year
    path('subjects/<int:subject_id>/years/<int:year>/pdfs/', PDFsBySubjectAndYearView.as_view(), name='pdfs-by-subject-year'),
    path('feedback/', FeedbackCreateView.as_view(), name='create-feedback'),
    path('feedback/list/', FeedbackListView.as_view(), name='list-feedback'),
]