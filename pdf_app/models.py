from django.db import models

class Topic(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='subjects')
    
    def __str__(self):
        return f"{self.topic.name} - {self.name}"

class PDFFile(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    year = models.PositiveIntegerField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='pdfs')
    file = models.FileField(upload_to='pdfs/')
    
    def __str__(self):
        return f"{self.title} ({self.year})"
    
    # Add to your existing models.py
class Feedback(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback from {self.name}"