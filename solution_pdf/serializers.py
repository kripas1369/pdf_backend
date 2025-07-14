from rest_framework import serializers
from .models import SolutionTopic, SolutionSubject, SolutionPDFFile, SolutionFeedback

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
        fields = ['id', 'title', 'subtitle', 'year', 'file', 'is_question']

class SolutionFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolutionFeedback
        fields = ['id', 'name', 'description', 'created_at']

class SolutionPDFGroupSerializer(serializers.Serializer):
    question = SolutionPDFFileSerializer()
    solution = SolutionPDFFileSerializer(required=False)
