"""
apps.users — Forms
"""
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class InviteUserForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(choices=User.Role.choices)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["role"]


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "bio", "phone", "avatar"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
        }
