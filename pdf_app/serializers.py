from rest_framework import serializers
from .models import Feedback, Topic, Subject, PDFFile

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'name']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name']

class YearSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    pdf_count = serializers.IntegerField()

class PDFFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDFFile
        fields = ['id', 'title', 'subtitle', 'year', 'file', 'is_solution']

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'name', 'description', 'created_at']

# Add this new serializer for grouped PDFs (questions with solutions)
class PDFGroupSerializer(serializers.Serializer):
    question = PDFFileSerializer()
    solution = PDFFileSerializer(required=False)  # Not all questions have solutions