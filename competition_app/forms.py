from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Judge

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label="First Name",
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'Enter judge\'s first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label="Last Name",
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'Enter judge\'s last name'
        })
    )
    
    email = forms.EmailField(
        required=True,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'Enter judge\'s email address'
        })
    )

    username = forms.CharField(
        label="Username",
        help_text="This will be used for login. Choose a unique username.",
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'Choose a username'
        })
    )

    password1 = forms.CharField(
        label="Password",
        help_text="Create a strong password with at least 8 characters",
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'Create a password'
        })
    )

    password2 = forms.CharField(
        label="Confirm Password",
        help_text="Enter the same password as above for verification",
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'Confirm your password'
        })
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use")
        return email

class JudgeForm(forms.ModelForm):
    phone = forms.CharField(
        label="Phone Number",
        help_text="Enter a valid contact number",
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'e.g., +1 234 567 8900'
        })
    )

    expertise = forms.CharField(
        label="Area of Expertise",
        help_text="Specify the judge's main area of expertise",
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'e.g., Classical Music, Modern Dance'
        })
    )

    bio = forms.CharField(
        label="Biography",
        help_text="Brief description of the judge's background and experience",
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'Enter judge\'s professional background and relevant experience...'
        })
    )

    profile_image = forms.ImageField(
        label="Profile Photo",
        help_text="Upload a professional photo (JPG, PNG)",
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
        })
    )

    status = forms.ChoiceField(
        label="Judge Status",
        help_text="Set the initial status of the judge",
        choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')],
        initial='ACTIVE',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
        })
    )

    class Meta:
        model = Judge
        fields = ['phone', 'profile_image', 'expertise', 'bio', 'status']
