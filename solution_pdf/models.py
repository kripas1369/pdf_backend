from django.db import models

class SolutionTopic(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class SolutionSubject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    topic = models.ForeignKey(SolutionTopic, on_delete=models.CASCADE, related_name='subjects')
    
    def __str__(self):
        return f"{self.topic.name} - {self.name}"

class SolutionPDFFile(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    year = models.PositiveIntegerField()
    subject = models.ForeignKey(SolutionSubject, on_delete=models.CASCADE, related_name='pdfs')
    file = models.FileField(upload_to='pdfs/')
    is_solution = models.BooleanField(default=False)  # Add this field
    
    def __str__(self):
        return f"{self.title} ({self.year})"
    
    # Add to your existing models.py
class SolutionFeedback(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback from {self.name}"
    # models.py

# from django.db import models

class SolutionUserQuery(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    topic = models.ForeignKey('SolutionTopic', on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.topic.name}"
