"""
apps.projects — Forms
"""
from django import forms
from .models import Project


class ProjectCreateForm(forms.Form):
    name = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    git_url = forms.CharField(max_length=500, label="Git Repository URL")
    git_branch = forms.CharField(max_length=100, initial="main")
    domain = forms.CharField(max_length=253, required=False, label="Domain (optional)")
    python_version = forms.ChoiceField(choices=Project.PythonVersion.choices)
    gunicorn_workers = forms.IntegerField(min_value=1, max_value=32, initial=3)
    django_settings_module = forms.CharField(max_length=200, initial="config.settings.production")


class ProjectUpdateForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "description",
            "git_branch",
            "domain",
            "gunicorn_workers",
            "django_settings_module",
            "health_check_url",
            "notes",
            "tags",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
