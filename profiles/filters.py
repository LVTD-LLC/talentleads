from django import forms
from django.db.models import Count
from django_filters import CharFilter, FilterSet, ModelMultipleChoiceFilter, NumberFilter
from django_filters.filters import MultipleChoiceFilter as BaseMultipleChoiceFilter

from profiles.choices import CapacityChoices

from .models import Profile, Technology


# Custom MultipleChoiceFilter that uses standard Django forms field to avoid Python 3.13 compatibility issues
class MultipleChoiceFilter(BaseMultipleChoiceFilter):
    field_class = forms.MultipleChoiceField


class ProfileFilter(FilterSet):
    title = CharFilter(lookup_expr="icontains")
    description = CharFilter(lookup_expr="icontains")

    # Using custom MultipleChoiceFilter to avoid Python 3.13 compatibility issues with django_filters
    city = MultipleChoiceFilter(widget=forms.CheckboxSelectMultiple, choices=[])
    state = MultipleChoiceFilter(widget=forms.CheckboxSelectMultiple, choices=[])
    country = MultipleChoiceFilter(widget=forms.CheckboxSelectMultiple, choices=[])

    level = MultipleChoiceFilter(widget=forms.CheckboxSelectMultiple, choices=[])
    tech_stack = ModelMultipleChoiceFilter(
        queryset=Technology.objects.annotate(profile_count=Count("profiles"))
        .filter(profile_count__gt=10)
        .order_by("-profile_count"),
        widget=forms.CheckboxSelectMultiple(),
        conjoined=True,
    )
    who_wants_to_be_hired_title = MultipleChoiceFilter(widget=forms.CheckboxSelectMultiple, choices=[])

    years_of_experience = NumberFilter()
    years_of_experience__gt = NumberFilter(field_name="years_of_experience", lookup_expr="gt")
    years_of_experience__lt = NumberFilter(field_name="years_of_experience", lookup_expr="lt")

    willing_to_relocate = MultipleChoiceFilter(widget=forms.CheckboxSelectMultiple, choices=[])

    capacity = MultipleChoiceFilter(
        choices=CapacityChoices.choices,
        widget=forms.CheckboxSelectMultiple,
        lookup_expr="icontains",
    )

    class Meta:
        model = Profile
        fields = [
            "title",
            "description",
            "level",
            "is_remote",
            "willing_to_relocate",
            "years_of_experience",
            "tech_stack",
            "who_wants_to_be_hired_title",
            "location",
            "city",
            "state",
            "country",
            "capacity",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically populate choices from database
        self.filters["city"].extra["choices"] = [
            (val, val)
            for val in Profile.objects.exclude(city="").values_list("city", flat=True).distinct().order_by("city")
        ]
        self.filters["state"].extra["choices"] = [
            (val, val)
            for val in Profile.objects.exclude(state="").values_list("state", flat=True).distinct().order_by("state")
        ]
        self.filters["country"].extra["choices"] = [
            (val, val)
            for val in Profile.objects.exclude(country="")
            .values_list("country", flat=True)
            .distinct()
            .order_by("country")
        ]
        self.filters["level"].extra["choices"] = [
            (val, val)
            for val in Profile.objects.exclude(level="").values_list("level", flat=True).distinct().order_by("level")
        ]
        self.filters["who_wants_to_be_hired_title"].extra["choices"] = [
            (val, val)
            for val in Profile.objects.exclude(who_wants_to_be_hired_title="")
            .values_list("who_wants_to_be_hired_title", flat=True)
            .distinct()
            .order_by("who_wants_to_be_hired_title")
        ]
        self.filters["willing_to_relocate"].extra["choices"] = [
            (val, val)
            for val in Profile.objects.exclude(willing_to_relocate="")
            .values_list("willing_to_relocate", flat=True)
            .distinct()
            .order_by("willing_to_relocate")
        ]
