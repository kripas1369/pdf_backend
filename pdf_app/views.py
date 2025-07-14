from rest_framework import viewsets, generics
from .models import Feedback, Topic, Subject, PDFFile
from .serializers import (FeedbackSerializer, PDFGroupSerializer, TopicSerializer, SubjectSerializer, 
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
    
class FeedbackCreateView(generics.CreateAPIView):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer

class FeedbackListView(generics.ListAPIView):
    queryset = Feedback.objects.all().order_by('-created_at')
    serializer_class = FeedbackSerializer

class PDFsBySubjectAndYearView(generics.ListAPIView):
    serializer_class = PDFGroupSerializer  # Changed from PDFFileSerializer

    def get_queryset(self):
        subject_id = self.kwargs['subject_id']
        year = self.kwargs['year']
        
        # Get all PDFs for this subject and year
        pdfs = PDFFile.objects.filter(subject_id=subject_id, year=year)
        
        # Group questions with their solutions
        result = []
        questions = pdfs.filter(is_solution=False)
        
        for question in questions:
            # Try to find a solution for this question
            solution = pdfs.filter(
                is_solution=True,
                title=question.title  # Assuming same title means they're paired
            ).first()
            
            result.append({
                'question': question,
                'solution': solution
            })
        
        return result

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)