from django import forms
from django.core.validators import MinValueValidator, RegexValidator

from .models import Item, Request, ResourceOffer

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

    class Meta:
        model = Request
        fields = [
            "submitted_by_name", "phone", "email",
            "for_someone_else", "beneficiary_name", "relationship",
            "people_count", "location", "additional_info",
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


class OfferForm(forms.ModelForm):
    valid_hours = forms.ChoiceField(
        choices=[("24", "24 hours"), ("48", "48 hours"), ("72", "72 hours")],
        initial="72",
        label="This offer stays valid for",
    )

    class Meta:
        model = ResourceOffer
        fields = ["item", "offered_by", "contact_phone", "quantity_available", "location"]
        labels = {
            "item": "What can you offer?",
            "offered_by": "Your name or organization",
            "contact_phone": "Phone number",
            "quantity_available": "How much can you provide?",
            "location": "Where is it available?",
        }
        widgets = {
            "offered_by": forms.TextInput(attrs={"placeholder": "e.g. Kisumu Relief Group"}),
            "contact_phone": forms.TextInput(attrs={"type": "tel", "placeholder": "e.g. 07XX XXX XXX"}),
            "quantity_available": forms.NumberInput(attrs={"min": 1}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Kondele, Kisumu"}),
        }

    def __init__(self, *args, incident=None, **kwargs):
        super().__init__(*args, **kwargs)
        items = Item.objects.all()
        if incident is not None:
            # Show only the items that fit this kind of disaster.
            keep = [i.pk for i in items if i.relevant_for(incident.hazard_type)]
            items = items.filter(pk__in=keep)
        self.fields["item"].queryset = items
        self.fields["item"].empty_label = "Choose an item"
        self.fields["item"].label_from_instance = lambda i: f"{i.get_category_display()}: {i.name} ({i.unit})"
        self.fields["contact_phone"].validators.append(phone_validator)
        self.fields["quantity_available"].validators.append(MinValueValidator(1))
