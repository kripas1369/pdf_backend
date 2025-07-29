from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SolutionFeedbackCreateView,
    SolutionFeedbackListView,
    SolutionTopicViewSet,
    SolutionSubjectByTopicView,
    SolutionUserQueryCreateView,
    SolutionYearListBySubjectView,
    SolutionPDFsBySubjectAndYearView
)

router = DefaultRouter()
router.register(r'stopics', SolutionTopicViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Get subjects for a specific topic
    path('topics/<int:topic_id>/subjects/', SolutionSubjectByTopicView.as_view(), name='subjects-by-topic'),
    # Get available years for a specific subject
    path('subjects/<int:subject_id>/years/', SolutionYearListBySubjectView.as_view(), name='years-by-subject'),
    # Get PDFs for a specific subject and year
    path('subjects/<int:subject_id>/years/<int:year>/pdfs/', SolutionPDFsBySubjectAndYearView.as_view(), name='pdfs-by-subject-year'),
    path('feedback/', SolutionFeedbackCreateView.as_view(), name='create-feedback'),
    path('feedback/list/', SolutionFeedbackListView.as_view(), name='list-feedback'),
    path('user-query/', SolutionUserQueryCreateView.as_view(), name='user-query-create'),

]