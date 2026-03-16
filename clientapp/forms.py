from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import (
    Lead, Client, Job, Product, Quote, ProductionUpdate,
    ProductImage, ProductTag, Vendor, LPO, Payment,
)
from django.contrib.auth.models import User
from .models import (ProductCategory, SystemSetting)
import re



class LeadForm(forms.ModelForm):
    account_manager = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='Account Manager').order_by('first_name'),
        required=False,
        empty_label='Select Account Manager',
        widget=forms.Select(attrs={'class': 'form-select w-full', 'id': 'id_account_manager'})
    )
   
    class Meta:
        model = Lead
        fields = [
            'name', 'email', 'phone', 'source', 'product_interest',
            'preferred_contact', 'follow_up_date', 'status', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Enter prospect name or company'}),
            'email': forms.EmailInput(attrs={'class': 'form-input w-full', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': '+254700000000'}),
            'source': forms.Select(attrs={'class': 'form-select w-full'}),
            'product_interest': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., Business Cards, Flyers'}),
            'preferred_contact': forms.Select(attrs={'class': 'form-select w-full'}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-input w-full', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select w-full'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 4, 'placeholder': 'Additional notes'}),
        }

    def clean_product_interest(self):
        # Get the list of selected products from the raw data
        products = self.data.getlist('product_interest')
        # Join them into a single string separated by commas
        return ", ".join(products)


class ClientForm(forms.ModelForm):
    account_manager = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='Account Manager').order_by('first_name'),
        required=False,
        empty_label='Select Account Manager',
        widget=forms.Select(attrs={'class': 'form-select w-full'})
    )
   
    class Meta:
        model = Client
        fields = [
            'client_type', 'name', 'company', 'email', 'phone',
            'vat_tax_id', 'kra_pin', 'address', 'industry',
            'payment_terms', 'credit_limit', 'default_markup', 'risk_rating', 'is_reseller',
            'delivery_address', 'delivery_instructions',
            'preferred_channel', 'lead_source', 'account_manager', 'status'
        ]
        widgets = {
            'client_type': forms.RadioSelect(attrs={'class': 'form-radio'}),
            'name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Client name'}),
            'company': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Company name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input w-full', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': '+1234567890'}),
            'vat_tax_id': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., P001234567A'}),
            'kra_pin': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., A001234567B'}),
            'address': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3, 'placeholder': 'Business address'}),
            'industry': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., Retail, Manufacturing'}),
            'payment_terms': forms.Select(attrs={'class': 'form-select w-full'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., 25000', 'step': '0.01'}),
            'default_markup': forms.NumberInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., 30', 'min': '0', 'max': '100', 'step': '0.01'}),
            'risk_rating': forms.Select(attrs={'class': 'form-select w-full'}),
            'is_reseller': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'delivery_address': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Default delivery address'}),
            'delivery_instructions': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3, 'placeholder': 'Delivery instructions'}),
            'preferred_channel': forms.Select(attrs={'class': 'form-select w-full'}),
            'lead_source': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., Referral, Website'}),
            'status': forms.Select(attrs={'class': 'form-select w-full'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()

        phone_cleaned = re.sub(r'[\s\-\(\)]', '', phone)

        kenyan_patterns = [
            r'^\+254[17]\d{8}$',
            r'^254[17]\d{8}$',
            r'^0[17]\d{8}$',
        ]
        is_valid = any(re.match(pattern, phone_cleaned) for pattern in kenyan_patterns)

        if not is_valid:
            raise ValidationError('Invalid Kenyan phone number format')
        
        if phone_cleaned.startswith('0'):
            phone_cleaned = '+254' + phone_cleaned[1:]
        elif phone_cleaned.startswith('254'):
            phone_cleaned = '+' + phone_cleaned

        if Client.objects.filter(phone=phone_cleaned).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError(
                f'A client with this phone number already exists.'
            )
    
        return phone_cleaned    


class QuoteForm(forms.ModelForm):
    client = forms.ModelChoiceField(
        queryset=Client.objects.filter(status='Active').order_by('name'),
        required=False,
        empty_label='Select Client (Optional)',
        widget=forms.Select(attrs={'class': 'form-select w-full'})
    )
    
    lead = forms.ModelChoiceField(
        queryset=Lead.objects.filter(status__in=['New', 'Contacted', 'Qualified']).order_by('name'),
        required=False,
        empty_label='Select Lead (Optional)',
        widget=forms.Select(attrs={'class': 'form-select w-full'})
    )
   
    class Meta:
        model = Quote
        fields = [
            'client', 'lead', 'product_name', 'quantity', 'unit_price',
            'payment_terms', 'include_vat', 'valid_until', 'notes', 'terms', 'status'
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Product name or description'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input w-full', 'placeholder': 'Quantity', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-input w-full', 'placeholder': 'Unit price', 'step': '0.01'}),
            'payment_terms': forms.Select(attrs={'class': 'form-select w-full'}),
            'include_vat': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'valid_until': forms.DateInput(attrs={'class': 'form-input w-full', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3, 'placeholder': 'Additional notes'}),
            'terms': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3, 'placeholder': 'Terms and conditions'}),
            'status': forms.Select(attrs={'class': 'form-select w-full'}),
        }


class ProductForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=ProductTag.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox'})
    )
   
    class Meta:
        model = Product
        fields = [
            'name', 'short_description', 'long_description', 'maintenance', 'technical_specs',
            'primary_category', 'sub_category', 'product_type', 'product_family',
            'tags', 'status', 'is_visible', 'visibility',
            'feature_product', 'bestseller_badge', 'new_arrival',
            'unit_of_measure', 'weight', 'weight_unit',
            'length', 'width', 'height', 'dimension_unit',
            'warranty', 'country_of_origin', 'internal_notes', 'client_notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Product name'}),
            'short_description': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Short description (max 150 chars)', 'maxlength': '150'}),
            'long_description': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 4, 'placeholder': 'Detailed description'}),
            'maintenance': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3, 'placeholder': 'Product maintenance details and care instructions'}),
            'technical_specs': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3, 'placeholder': 'Technical specifications'}),
            'primary_category': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., Print Products, Signage'}),
            'sub_category': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., Business Cards, Flyers'}),
            'product_type': forms.Select(attrs={'class': 'form-select w-full'}),
            'product_family': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., Business Cards Family'}),
            'status': forms.Select(attrs={'class': 'form-select w-full'}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'visibility': forms.Select(attrs={'class': 'form-select w-full'}),
            'feature_product': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'bestseller_badge': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'new_arrival': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'unit_of_measure': forms.Select(attrs={'class': 'form-select w-full'}),
            'weight': forms.NumberInput(attrs={'class': 'form-input w-full', 'placeholder': 'Weight', 'step': '0.01'}),
            'weight_unit': forms.Select(attrs={'class': 'form-select w-full'}),
            'length': forms.NumberInput(attrs={'class': 'form-input w-full', 'placeholder': 'Length', 'step': '0.01'}),
            'width': forms.NumberInput(attrs={'class': 'form-input w-full', 'placeholder': 'Width', 'step': '0.01'}),
            'height': forms.NumberInput(attrs={'class': 'form-input w-full', 'placeholder': 'Height', 'step': '0.01'}),
            'dimension_unit': forms.Select(attrs={'class': 'form-select w-full'}),
            'warranty': forms.Select(attrs={'class': 'form-select w-full'}),
            'country_of_origin': forms.Select(attrs={'class': 'form-select w-full'}),
            'internal_notes': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 2, 'placeholder': 'Internal use only'}),
            'client_notes': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 2, 'placeholder': 'Visible to clients'}),
        }


class JobForm(forms.ModelForm):
    """Form for creating/editing jobs"""
    
    class Meta:
        model = Job
        fields = ['client', 'quote', 'job_name', 'job_type', 'priority', 'product', 
                  'quantity', 'person_in_charge', 'status', 'start_date', 
                  'expected_completion', 'delivery_method', 'notes']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select w-full'}),
            'quote': forms.Select(attrs={'class': 'form-select w-full'}),
            'job_name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Enter job name'}),
            'job_type': forms.Select(attrs={'class': 'form-select w-full'}),
            'priority': forms.Select(attrs={'class': 'form-select w-full'}),
            'product': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Main product'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input w-full', 'min': '1'}),
            'person_in_charge': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Person responsible'}),
            'status': forms.Select(attrs={'class': 'form-select w-full'}),
            'start_date': forms.DateInput(attrs={'class': 'form-input w-full', 'type': 'date'}),
            'expected_completion': forms.DateInput(attrs={'class': 'form-input w-full', 'type': 'date'}),
            'delivery_method': forms.Select(attrs={'class': 'form-select w-full'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 4}),
        }


class QuoteCostingForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = [
            'unit_price', 'production_cost', 'production_status',
            'production_notes', 'status', 'payment_terms', 'include_vat'
        ]
        widgets = {
            'unit_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'production_cost': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'production_status': forms.Select(attrs={'class': 'form-select'}),
            'production_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'payment_terms': forms.Select(attrs={'class': 'form-select'}),
            'include_vat': forms.CheckboxInput(attrs={'class': 'h-4 w-4'}),
        }


class ProductionUpdateForm(forms.ModelForm):
    class Meta:
        model = ProductionUpdate
        fields = ['status', 'progress', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'progress': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'max': '100'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }


class VendorForm(forms.ModelForm):
    """Form for creating/editing vendors"""
    
    class Meta:
        model = Vendor
        fields = [
            'user',
            'name', 'contact_person', 'email', 'phone', 'business_address',
            'tax_pin', 'payment_terms', 'payment_method', 'services', 
            'specialization', 'minimum_order', 'lead_time', 'rush_capable',
            'quality_rating', 'reliability_rating', 'vps_score_value',
            'rating', 'internal_notes', 'recommended', 'active'
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select w-full'}),
            'name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Vendor name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Contact person'}),
            'email': forms.EmailInput(attrs={'class': 'form-input w-full', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Phone'}),
            'business_address': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3}),
            'tax_pin': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Tax PIN'}),
            'payment_terms': forms.Select(attrs={'class': 'form-select w-full'}),
            'payment_method': forms.Select(attrs={'class': 'form-select w-full'}),
            'services': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 2, 'placeholder': 'Comma-separated services'}),
            'specialization': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 2}),
            'minimum_order': forms.NumberInput(attrs={'class': 'form-input w-full', 'step': '0.01'}),
            'lead_time': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g., 5 days'}),
            'rush_capable': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'quality_rating': forms.Select(attrs={'class': 'form-select w-full'}),
            'reliability_rating': forms.Select(attrs={'class': 'form-select w-full'}),
            'vps_score_value': forms.NumberInput(attrs={'class': 'form-input w-full', 'step': '0.01'}),
            'rating': forms.NumberInput(attrs={'class': 'form-input w-full', 'step': '0.1', 'min': '0', 'max': '5'}),
            'internal_notes': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 4}),
            'recommended': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'active': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
        }


class LPO_Form(forms.ModelForm):
    """Form for creating/editing LPOs"""
    
    class Meta:
        model = LPO
        fields = ['client', 'quote', 'status', 'subtotal', 'vat_amount', 'total_amount',
                  'payment_terms', 'delivery_date', 'notes', 'terms_and_conditions']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select w-full'}),
            'quote': forms.Select(attrs={'class': 'form-select w-full'}),
            'status': forms.Select(attrs={'class': 'form-select w-full'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-input w-full', 'step': '0.01'}),
            'vat_amount': forms.NumberInput(attrs={'class': 'form-input w-full', 'step': '0.01'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-input w-full', 'step': '0.01'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-input w-full'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-input w-full', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 4}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 4}),
        }


class PaymentForm(forms.ModelForm):
    """Form for creating/editing payments"""
    
    class Meta:
        model = Payment
        fields = ['lpo', 'payment_date', 'amount', 'payment_method', 'status', 
                  'reference_number', 'notes']
        widgets = {
            'lpo': forms.Select(attrs={'class': 'form-select w-full'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-input w-full', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input w-full', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select w-full'}),
            'status': forms.Select(attrs={'class': 'form-select w-full'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Payment reference'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 4}),
        }


class UserForm(forms.ModelForm):
    """Form for creating/editing users"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input w-full'}),
        required=False,
        help_text="Leave blank to keep current password"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-input w-full', 'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Last name'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


# ==================== ADMIN FORMS ====================

class AdminClientForm(ClientForm):
    """Extended form for Admins with ALL fields"""
    class Meta(ClientForm.Meta):
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any admin-specific field customizations here
        # Make all fields editable for admin
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' admin-field'

class AdminProductForm(ProductForm):
    """Extended form for Admins with ALL fields"""
    class Meta(ProductForm.Meta):
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add admin-specific field customizations
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' admin-field'

