from rest_framework import viewsets, generics
from .models import Topic, Subject, PDFFile
from .serializers import (TopicSerializer, SubjectSerializer, 
                         YearSerializer, PDFFileSerializer)
from django.db.models import Count

class TopicViewSet(viewsets.ModelViewSet):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer

class SubjectByTopicView(generics.ListAPIView):
    serializer_class = SubjectSerializer
    
    def get_queryset(self):
        topic_id = self.kwargs['topic_id']
        return Subject.objects.filter(topic_id=topic_id)

class YearListBySubjectView(generics.ListAPIView):
    serializer_class = YearSerializer
    
    def get_queryset(self):
        subject_id = self.kwargs['subject_id']
        years = PDFFile.objects.filter(subject_id=subject_id)\
                              .values('year')\
                              .annotate(pdf_count=Count('id'))\
                              .order_by('-year')
        return [{'year': item['year'], 'pdf_count': item['pdf_count']} for item in years]

class PDFsBySubjectAndYearView(generics.ListAPIView):
    serializer_class = PDFFileSerializer
    
    def get_queryset(self):
        subject_id = self.kwargs['subject_id']
        year = self.kwargs['year']
        return PDFFile.objects.filter(subject_id=subject_id, year=year)