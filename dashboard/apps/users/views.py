"""
apps.users — Views
"""
import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView

from apps.core.mixins import AdminRequiredMixin, OperatorRequiredMixin
from .forms import InviteUserForm, UserRoleForm, UserProfileForm
from .services import UserService

logger = logging.getLogger(__name__)
User = get_user_model()


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "users/list.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        return User.objects.order_by("role", "username")


@method_decorator(login_required, name="dispatch")
class InviteUserView(AdminRequiredMixin, View):
    template_name = "users/invite.html"

    def get(self, request):
        form = InviteUserForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = InviteUserForm(request.POST)
        if form.is_valid():
            try:
                svc = UserService(acting_user=request.user)
                user = svc.create_user(
                    username=form.cleaned_data["username"],
                    email=form.cleaned_data["email"],
                    role=form.cleaned_data["role"],
                    first_name=form.cleaned_data.get("first_name", ""),
                    last_name=form.cleaned_data.get("last_name", ""),
                )
                messages.success(request, f"Invited {user.username} successfully. An email has been sent.")
                return redirect("users:list")
            except ValueError as exc:
                messages.error(request, str(exc))

        return render(request, self.template_name, {"form": form})


@method_decorator(login_required, name="dispatch")
class UserDetailView(AdminRequiredMixin, View):
    template_name = "users/detail.html"

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        role_form = UserRoleForm(instance=user)
        return render(request, self.template_name, {"target_user": user, "role_form": role_form})


@method_decorator(login_required, name="dispatch")
class ChangeRoleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserRoleForm(request.POST, instance=user)
        if form.is_valid():
            svc = UserService(acting_user=request.user)
            svc.change_role(user, form.cleaned_data["role"])
            messages.success(request, f"Role updated for {user.username}.")
        return redirect("users:detail", pk=pk)


@method_decorator(login_required, name="dispatch")
class ToggleUserActiveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        svc = UserService(acting_user=request.user)
        if user.is_active:
            svc.deactivate_user(user)
            messages.warning(request, f"Deactivated {user.username}.")
        else:
            svc.activate_user(user)
            messages.success(request, f"Activated {user.username}.")
        return redirect("users:list")


@method_decorator(login_required, name="dispatch")
class ProfileView(View):
    template_name = "users/profile.html"

    def get(self, request):
        form = UserProfileForm(instance=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("users:profile")
        return render(request, self.template_name, {"form": form})
