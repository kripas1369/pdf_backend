from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SolutionTopicViewSet,
    SolutionSubjectByTopicView,
    SolutionYearListBySubjectView,
    SolutionPDFsBySubjectAndYearView,
    SolutionFeedbackCreateView,
    SolutionFeedbackListView,
)

router = DefaultRouter()
router.register(r'topics', SolutionTopicViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('topics/<int:topic_id>/subjects/', SolutionSubjectByTopicView.as_view(), name='solution-subjects-by-topic'),
    path('subjects/<int:subject_id>/years/', SolutionYearListBySubjectView.as_view(), name='solution-years-by-subject'),
    path('subjects/<int:subject_id>/years/<int:year>/pdfs/', SolutionPDFsBySubjectAndYearView.as_view(), name='solution-pdfs-by-subject-year'),
    path('feedback/', SolutionFeedbackCreateView.as_view(), name='solution-feedback-create'),
    path('feedback/list/', SolutionFeedbackListView.as_view(), name='solution-feedback-list'),
]
