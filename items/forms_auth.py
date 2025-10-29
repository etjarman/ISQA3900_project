from django.contrib.auth.forms import UserCreationForm
from django.utils.safestring import mark_safe

ASCII_HELP = mark_safe("""
<ul style="margin-top:0.5rem">
  <li>Your password can't be too similar to your other personal information.</li>
  <li>Your password must contain at least 8 characters.</li>
  <li>Your password can't be a commonly used password.</li>
  <li>Your password can't be entirely numeric.</li>
</ul>
""")

class SignupForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = ASCII_HELP
