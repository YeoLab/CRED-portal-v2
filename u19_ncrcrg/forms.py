from datetime import date

# from crispy_forms.layout import Submit, Layout, Row, Column, Field, Fieldset, ButtonHolder
from django import forms
from crispy_forms.helper import FormHelper


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Data portal username ( usually an email )',
                'size': 35,
                'class': 'form-control'
            }
        )
    )
    pwd = forms.CharField(
        max_length=30,
        required=True,
        label='Password',
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Password',
                'size': 35,
                'class': 'form-control'
            }
        )
    )


class CreateAccountForm(forms.Form):
    firstname = forms.CharField(
        required=True, max_length=30,
        label='First Name'
    )
    lastname = forms.CharField(
        required=True,
        max_length=30,
        label='Last Name'
    )
    email = forms.EmailField(
        required=True,
        max_length=30,
        label='Email'
    )
    institution = forms.CharField(
        required=True,
        max_length=30,
        label='Institution Name'
    )
    lab = forms.CharField(
        required=True,
        max_length=30,
        label='Associated Lab'
    )


class DynamicForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.dynamic_fields = kwargs.pop('dynamic_fields')
        self.my_files = kwargs.pop('my_files')
        # super(DynamicForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        for key, fields in self.dynamic_fields.items():
            for field in fields:
                if key == 'integer_inputs':
                    self.fields[field[1]] = forms.IntegerField(
                        label=field[0],
                        initial=field[2],
                    )
                elif key == 'float_inputs':
                    self.fields[field[1]] = forms.FloatField(
                        label=field[0],
                        initial=field[2],
                    )
                elif key == 'dropdown_inputs':
                    self.fields[field[1]] = forms.CharField(
                        label=field[0],
                        widget=forms.Select(choices=field[2])
                    )
                elif key == 'file_inputs':
                    if self.my_files:
                        choices = [
                            (f, f) for f in self.my_files if f.endswith(field[2])
                        ] if field[2] is not None else \
                        [(f, f) for f in self.my_files]
                    else:
                        choices = []
                    if len(field) == 4:  # if we want to provide the option for users to select either provided files, or their own (provided files in field[3])
                        if type(field[3]) == list:
                            default_choices = [(f, f) for f in field[3]]
                            choices = default_choices + choices
                        elif type(field[3]) == str:
                            default_choices = [(field[3], field[3])]
                            choices = default_choices + choices

                    self.fields[field[1]] = forms.CharField(
                        label=field[0],
                        widget=forms.Select(
                            choices=choices,
                        ),
                        help_text="If this is blank, please use the Globus file helper page to select files."
                    )
                elif key == 'multi_file_inputs':
                    if self.my_files:
                        choices = [
                            (f, f) for f in self.my_files if f.endswith(field[2])
                        ] if field[2] is not None else \
                        [(f, f) for f in self.my_files]
                    else:
                        choices = []
                    self.fields[field[1]] = forms.CharField(
                        label=field[0],
                        widget=forms.SelectMultiple(
                            choices=choices,
                        )
                    )

                elif key == 'textarea_inputs':
                    self.fields[field[1]] = forms.CharField(
                        label=field[0],
                        widget=forms.Textarea,
                        initial=field[2],
                    )
                elif key == 'text_inputs':
                    if len(field) > 3:  # extra args such as validator/conditionals
                        self.fields[field[1]] = forms.CharField(
                            label=field[0],
                            widget=forms.TextInput,
                            initial=field[2],
                            validators=field[3],
                        )
                    else:
                        self.fields[field[1]] = forms.CharField(
                            label=field[0],
                            widget=forms.TextInput,
                            initial=field[2],
                        )
                elif key == 'date_inputs':
                    self.fields[field[1]] = forms.DateField(
                        label=field[0],
                        widget=forms.DateInput(attrs={'type': 'date'}),
                        initial=date.today,
                    )
                elif key == 'hidden':
                    self.fields[field[1]] = forms.CharField(
                        label=field[0],
                        widget=forms.HiddenInput,
                        initial=field[2]
                    )
                else:
                    pass
        #  TODO: django-crispy-forms cannot be stylized here?
        # self.helper.filter_by_widget(forms.Select).wrap(Field, css_class="form-select form-select-lg mb-3")

        # self.helper.add_input(Submit('submit', 'Submit', css_class='btn-primary'))
        # self.helper.layout = Layout(
        #     Field('Organism', css_class="form-select form-select-xl mb-2")
        # )
        # self.helper = [Layout(x) for x in self.helper]
        # print(self.helper[2])
        self.helper.form_method = 'POST'

    def clean(self):
        """
        Currently does nothing. dynamic_fields will be specific to each DynamicForm
        object, so this function should generalize across forms with different required fields.
        """
        """
        for _, fields in self.dynamic_fields.items():
            for field in fields:
                print(f"Field: {field}")

        cleaned_data = super().clean()
        organism = cleaned_data.get("organism")
        if organism == 'error':
            print(f"organism: {organism}")
            raise ValidationError("Passwords did not match")
        """
        pass


class PublicationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.title = kwargs.pop('title')
        self.authors = kwargs.pop('authors')
        self.full_authors = kwargs.pop('full_authors')
        self.abstract = kwargs.pop('abstract')
        self.geo_accessions = kwargs.pop('geo_accessions')
        self.pride_accessions = kwargs.pop('pride_accessions')
        self.omero_accessions = kwargs.pop('omero_accessions')
        self.pub_year = kwargs.pop('pub_year')
        self.total_citations = kwargs.pop('total_citations')
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        geo_accessions = []
        pride_accessions = []
        omero_accessions = []
        for accession in self.geo_accessions:
            geo_accessions.append(accession)
        for accession in self.pride_accessions:
            pride_accessions.append(accession)
        for accession in self.omero_accessions:
            omero_accessions.append(accession)

        self.fields['geo_accessions'] = forms.MultipleChoiceField(
            label='Select files to import:',
            choices=geo_accessions,
            widget=forms.SelectMultiple(attrs={'size': min(10, len(geo_accessions)), 'width': 15})
        )
        self.fields['pride_accessions'] = forms.MultipleChoiceField(
            label='Select files to import:',
            choices=pride_accessions,
            widget=forms.SelectMultiple(attrs={'size': min(10, len(pride_accessions)), 'width': 15})
        )
        self.fields['omero_accessions'] = forms.MultipleChoiceField(
            label='Select files to import:',
            choices=omero_accessions,
            widget=forms.SelectMultiple(attrs={'size': min(10, len(omero_accessions)), 'width': 15})
        )
        self.helper.form_method = 'POST'

    def clean(self):
        """
        Currently does nothing.
        """
        pass