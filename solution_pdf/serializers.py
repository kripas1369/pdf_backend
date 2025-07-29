from rest_framework import serializers
from .models import SolutionFeedback, SolutionTopic, SolutionSubject, SolutionPDFFile, SolutionUserQuery

class SolutionTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolutionTopic
        fields = ['id', 'name']

class SolutionSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolutionSubject
        fields = ['id', 'name']

class SolutionYearSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    pdf_count = serializers.IntegerField()

class SolutionPDFFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolutionPDFFile
        fields = ['id', 'title', 'subtitle', 'year', 'file']

        # Add to your existing serializers.py
class SolutionFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolutionFeedback
        fields = ['id', 'name', 'description', 'created_at']


class SolutionUserQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SolutionUserQuery
        fields = ['id', 'name', 'email', 'topic', 'submitted_at']
        read_only_fields = ['submitted_at']