from django import forms
from apps.users.models import User, Role
from apps.tasks.models import Task, TaskComment, TaskAttachment


class UserAutocompleteWidget(forms.Select):
    """Custom select widget that doesn't load the full queryset into HTML."""
    def optgroups(self, name, value, attrs=None):
        groups = []
        if value and value[0]:
            try:
                user = User.objects.get(pk=value[0])
                groups.append((None, [self.create_option(name, user.pk, user.username, True, 0, subindex=None, attrs=attrs)], 0))
            except User.DoesNotExist:
                pass
        return groups


class UserAutocompleteMultipleWidget(forms.SelectMultiple):
    """Custom multi-select widget that doesn't load the full queryset into HTML."""
    def optgroups(self, name, value, attrs=None):
        groups = []
        if value:
            selected_users = User.objects.filter(pk__in=[v for v in value if v])
            options = []
            for i, user in enumerate(selected_users):
                options.append(self.create_option(name, user.pk, user.username, True, i, subindex=None, attrs=attrs))
            if options:
                groups.append((None, options, 0))
        return groups


class UserForm(forms.ModelForm):
    """Create/Edit user form."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Leave blank to keep current password.',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role',
                  'department', 'is_active_employee', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active_employee': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class TaskForm(forms.ModelForm):
    """Create/Edit task form."""
    class Meta:
        model = Task
        fields = ['title', 'description', 'creator', 'reviewer', 'assignees', 'status',
                  'priority', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'creator': UserAutocompleteWidget(attrs={'class': 'form-select user-autocomplete'}),
            'reviewer': UserAutocompleteWidget(attrs={'class': 'form-select user-autocomplete'}),
            'assignees': UserAutocompleteMultipleWidget(attrs={'class': 'form-select user-autocomplete'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reviewer'].queryset = User.objects.filter(
            role__in=[Role.MANAGER, Role.SUPERADMIN]
        )
        self.fields['reviewer'].required = False
        self.fields['assignees'].queryset = User.objects.filter(is_active=True)
        self.fields['assignees'].required = False
        self.fields['due_date'].required = False


class TaskCommentForm(forms.ModelForm):
    """Add comment to task."""
    class Meta:
        model = TaskComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add a comment...',
            }),
        }


class TaskAttachmentForm(forms.Form):
    """Upload attachment to task."""
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )


class SendNotificationForm(forms.Form):
    """Send ad-hoc notification + email to a user."""
    recipient = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=UserAutocompleteWidget(attrs={'class': 'form-select user-autocomplete'}),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
    send_email = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Also send email',
    )


class TaskAssigneesForm(forms.Form):
    """Manage task assignees."""
    assignees = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=UserAutocompleteMultipleWidget(attrs={'class': 'form-select user-autocomplete'}),
        required=False,
    )
