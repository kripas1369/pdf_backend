from rest_framework import viewsets, generics

from django.db.models import Count

from solution_pdf.models import SolutionFeedback, SolutionPDFFile, SolutionSubject, SolutionTopic, SolutionUserQuery
from solution_pdf.serializers import SolutionFeedbackSerializer, SolutionPDFFileSerializer, SolutionSubjectSerializer, SolutionTopicSerializer, SolutionUserQuerySerializer, SolutionYearSerializer

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
        years = SolutionPDFFile.objects.filter(subject_id=subject_id)\
                              .values('year')\
                              .annotate(pdf_count=Count('id'))\
                              .order_by('-year')
        return [{'year': item['year'], 'pdf_count': item['pdf_count']} for item in years]

class SolutionPDFsBySubjectAndYearView(generics.ListAPIView):
    serializer_class = SolutionPDFFileSerializer
    
    def get_queryset(self):
        subject_id = self.kwargs['subject_id']
        year = self.kwargs['year']
        return SolutionPDFFile.objects.filter(subject_id=subject_id, year=year)
    
class SolutionFeedbackCreateView(generics.CreateAPIView):
    queryset = SolutionFeedback.objects.all()
    serializer_class = SolutionFeedbackSerializer

class SolutionFeedbackListView(generics.ListAPIView):
    queryset = SolutionFeedback.objects.all().order_by('-created_at')
    serializer_class = SolutionFeedbackSerializer

class SolutionUserQueryCreateView(generics.CreateAPIView):
    queryset = SolutionUserQuery.objects.all()
    serializer_class = SolutionUserQuerySerializer