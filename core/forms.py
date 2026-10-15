from django import forms
from django.core.validators import RegexValidator

from .models import Request

phone_validator = RegexValidator(
    r"^\+?[0-9 ]{9,15}$",
    "Enter a valid phone number, for example 0712 345 678.",
)


class HelpRequestForm(forms.ModelForm):
    for_someone_else = forms.TypedChoiceField(
        choices=[("False", "For myself"), ("True", "For someone else")],
        coerce=lambda v: v == "True",
        widget=forms.RadioSelect,
        initial="False",
    )
    need_type = forms.ChoiceField(
        choices=Request.NEED_CHOICES,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Request
        fields = [
            "submitted_by_name", "phone", "email",
            "for_someone_else", "beneficiary_name", "relationship",
            "need_type", "people_count", "location", "additional_info",
        ]
        widgets = {
            "submitted_by_name": forms.TextInput(attrs={"placeholder": "e.g. John Mwangi", "autocomplete": "name"}),
            "phone": forms.TextInput(attrs={"type": "tel", "placeholder": "e.g. 07XX XXX XXX", "autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"placeholder": "e.g. example@domain.com"}),
            "beneficiary_name": forms.TextInput(attrs={"placeholder": "Name of the person who needs help"}),
            "relationship": forms.TextInput(attrs={"placeholder": "e.g. family member, neighbour"}),
            "people_count": forms.NumberInput(attrs={"min": 1}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Mamboleo, Kisumu"}),
            "additional_info": forms.Textarea(attrs={"rows": 5, "placeholder": "Anything else we should know, such as landmarks, medical needs or access problems."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].validators.append(phone_validator)

    def clean(self):
        data = super().clean()
        someone_else = data.get("for_someone_else")
        if someone_else and not (data.get("beneficiary_name") or "").strip():
            self.add_error("beneficiary_name", "Tell us the name of the person you are requesting help for.")
        if not someone_else:
            data["beneficiary_name"] = ""
            data["relationship"] = ""
        return data
