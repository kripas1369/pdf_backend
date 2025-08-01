from rest_framework import serializers
from .models import Feedback, Topic, Subject, PDFFile, UserQuery

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
        fields = ['id', 'title', 'subtitle', 'year', 'file']

        # Add to your existing serializers.py
class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'name', 'description', 'created_at']


class UserQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserQuery
        fields = ['id', 'name', 'email', 'topic', 'submitted_at']
        read_only_fields = ['submitted_at']