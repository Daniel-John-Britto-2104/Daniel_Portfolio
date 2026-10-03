from django.db import models
from django.utils.text import slugify


class Profile(models.Model):
    full_name = models.CharField(max_length=150, default="Daniel John Britto")
    title = models.CharField(max_length=255, default="Python Backend Developer | Django & Flask Developer")
    headline = models.CharField(max_length=255, default="Passionate Backend Developer specializing in scalable Python web applications and API integration.")
    bio = models.TextField(
        default="I am a dedicated Python Backend Developer with hands-on experience building robust APIs, web applications, and database architectures. Proficient in Django, Flask, PostgreSQL, MySQL, and modern backend practices."
    )
    years_of_experience = models.PositiveIntegerField(default=1)
    projects_completed = models.PositiveIntegerField(default=8)
    location = models.CharField(max_length=150, default="India")
    email = models.EmailField(default="danieljohnbrittoaj@gmail.com")
    phone = models.CharField(max_length=30, blank=True, default="+91 98765 43210")
    resume_url = models.CharField(max_length=500, blank=True, default="#")
    profile_image_url = models.CharField(max_length=500, blank=True, default="/static/images/profile.svg")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self):
        return f"{self.full_name} ({self.title})"


class SocialLink(models.Model):
    platform = models.CharField(max_length=50, help_text="e.g. GitHub, LinkedIn, Email, Twitter")
    url = models.URLField(max_length=500)
    icon_name = models.CharField(max_length=50, help_text="e.g. github, linkedin, mail, code")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.platform} - {self.url}"


class Skill(models.Model):
    CATEGORY_CHOICES = [
        ("Languages", "Languages"),
        ("Frameworks", "Frameworks & Libraries"),
        ("Databases", "Databases"),
        ("Tools", "Tools & Platforms"),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    proficiency = models.PositiveIntegerField(default=85, help_text="Percentage score between 1 and 100")
    icon_name = models.CharField(max_length=50, blank=True, default="code", help_text="Icon identifier e.g. python, django, database")
    is_featured = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.category} - {self.proficiency}%)"


class Experience(models.Model):
    company = models.CharField(max_length=200)
    role = models.CharField(max_length=150)
    location = models.CharField(max_length=150, blank=True, default="India")
    is_current = models.BooleanField(default=False)
    start_date = models.CharField(max_length=50, help_text="e.g. Nov 2024 or 2024")
    end_date = models.CharField(max_length=50, blank=True, default="Present", help_text="e.g. Present or Dec 2024")
    description = models.TextField(blank=True)
    responsibilities_raw = models.TextField(
        help_text="Bullet points or newline/comma separated responsibilities",
        blank=True
    )
    tech_stack = models.CharField(max_length=255, blank=True, help_text="e.g. Python, Flask, Angular, PostgreSQL")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-id"]
        verbose_name_plural = "Experiences"

    def __str__(self):
        return f"{self.role} at {self.company}"

    def responsibilities_list(self):
        if not self.responsibilities_raw:
            return []
        lines = [line.strip().lstrip("•- ") for line in self.responsibilities_raw.splitlines() if line.strip()]
        return lines


class Project(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.TextField()
    description = models.TextField(blank=True)
    image_url = models.CharField(max_length=500, blank=True, default="/static/images/project-placeholder.svg")
    tech_stack = models.CharField(max_length=255, help_text="Comma-separated e.g. Python, Django, PostgreSQL")
    features_raw = models.TextField(blank=True, help_text="Newline separated key features")
    github_url = models.URLField(max_length=500, blank=True, default="https://github.com")
    live_url = models.URLField(max_length=500, blank=True)
    is_featured = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def tech_list(self):
        if not self.tech_stack:
            return []
        return [t.strip() for t in self.tech_stack.split(",") if t.strip()]

    def features_list(self):
        if not self.features_raw:
            return []
        return [f.strip().lstrip("•- ") for f in self.features_raw.splitlines() if f.strip()]


class Education(models.Model):
    degree = models.CharField(max_length=200)
    institution = models.CharField(max_length=250)
    score = models.CharField(max_length=100, help_text="e.g. 8.2 CGPA or 85%")
    location = models.CharField(max_length=150, blank=True)
    start_year = models.CharField(max_length=20)
    end_year = models.CharField(max_length=20)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-id"]
        verbose_name_plural = "Education Records"

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class Certificate(models.Model):
    title = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200)
    issue_date = models.CharField(max_length=50)
    credential_url = models.URLField(max_length=500, blank=True)
    image_url = models.CharField(max_length=500, blank=True, default="/static/images/certificate-placeholder.svg")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-id"]

    def __str__(self):
        return f"{self.title} by {self.issuer}"


class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"

    def __str__(self):
        return f"Message from {self.name}" + (f" - {self.subject}" if self.subject else "")
