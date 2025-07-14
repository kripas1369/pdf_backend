from rest_framework import viewsets, generics
from django.db.models import Count
from .models import SolutionTopic, SolutionSubject, SolutionPDFFile, SolutionFeedback
from .serializers import (
    SolutionTopicSerializer, SolutionSubjectSerializer, SolutionYearSerializer,
    SolutionPDFFileSerializer, SolutionPDFGroupSerializer, SolutionFeedbackSerializer
)

class SolutionTopicViewSet(viewsets.ModelViewSet):
    queryset = SolutionTopic.objects.all()
    serializer_class = SolutionTopicSerializer

class SolutionSubjectByTopicView(generics.ListAPIView):
    serializer_class = SolutionSubjectSerializer

    def get_queryset(self):
        topic_id = self.kwargs['topic_id']
        return SolutionSubject.objects.filter(topic_id=topic_id)

class SolutionYearListBySubjectView(generics.ListAPIView):
    serializer_class = SolutionYearSerializer

    def get_queryset(self):
        subject_id = self.kwargs['subject_id']
        return SolutionPDFFile.objects.filter(subject_id=subject_id)\
            .values('year')\
            .annotate(pdf_count=Count('id'))\
            .order_by('-year')

class SolutionPDFsBySubjectAndYearView(generics.ListAPIView):
    serializer_class = SolutionPDFGroupSerializer

    def get_queryset(self):
        subject_id = self.kwargs['subject_id']
        year = self.kwargs['year']
        pdfs = SolutionPDFFile.objects.filter(subject_id=subject_id, year=year)
        questions = pdfs.filter(is_question=True)

        result = []
        for question in questions:
            solution = pdfs.filter(title=question.title, is_question=False).first()
            result.append({'question': question, 'solution': solution})

        return result

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class SolutionFeedbackCreateView(generics.CreateAPIView):
    queryset = SolutionFeedback.objects.all()
    serializer_class = SolutionFeedbackSerializer

class SolutionFeedbackListView(generics.ListAPIView):
    queryset = SolutionFeedback.objects.all().order_by('-created_at')
    serializer_class = SolutionFeedbackSerializer
