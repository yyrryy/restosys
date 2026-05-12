from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import BaseFormSet, formset_factory
from django.contrib.auth import get_user_model

from .models import CashDeskEntry, DiningTable, InventoryItem, MenuCategory, MenuItem, Purchase, PurchaseItem, RecipeComponent, Supplier, UserProfile


class DiningTableForm(forms.ModelForm):
    class Meta:
        model = DiningTable
        fields = ['name', 'seats', 'status']


class MenuItemForm(forms.ModelForm):
    category = forms.ChoiceField(choices=())

    class Meta:
        model = MenuItem
        fields = ['name', 'category', 'price', 'image', 'is_available']
        labels = {
            'image': 'Image',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        category_choices = [(category.name, category.name) for category in MenuCategory.objects.all()]
        self.fields['category'].choices = category_choices
        if not category_choices:
            self.fields['category'].help_text = 'Create at least one category first.'


class InventoryItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['name', 'price', 'quantity', 'unit', 'reorder_level']:
            self.fields[field_name].required = True

    class Meta:
        model = InventoryItem
        fields = ['name', 'plu', 'price', 'quantity', 'unit', 'reorder_level']


class InventoryItemInfoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['name', 'price', 'unit', 'reorder_level']:
            self.fields[field_name].required = True

    class Meta:
        model = InventoryItem
        fields = ['name', 'plu', 'price', 'unit', 'reorder_level']


class MenuCategoryForm(forms.ModelForm):
    class Meta:
        model = MenuCategory
        fields = ['name']


class RecipeComponentForm(forms.ModelForm):
    class Meta:
        model = RecipeComponent
        fields = ['menu_item', 'inventory_item', 'quantity']


class OrderCreateForm(forms.Form):
    table = forms.ModelChoiceField(queryset=DiningTable.objects.none())
    customer_name = forms.CharField(max_length=120, required=False)

    def __init__(self, *args, **kwargs):
        menu_items = kwargs.pop('menu_items')
        # require_table = kwargs.pop('require_table', True)
        include_waiter_choice = kwargs.pop('include_waiter_choice', False)
        super().__init__(*args, **kwargs)
        self.fields['table'].queryset = DiningTable.objects.all()
        # self.fields['table'].required = require_table

        if include_waiter_choice:
            User = get_user_model()
            self.fields['cashier_waiter'] = forms.ModelChoiceField(
                label='Waiter',
                queryset=User.objects.filter(profile__role=UserProfile.ROLE_WAITER),
                required=False,
                empty_label='No waiter',
            )

        for item in menu_items:
            self.fields[f'item_{item.pk}'] = forms.IntegerField(
                label=f'{item.name} - {item.price}',
                min_value=0,
                required=False,
                initial=0,
            )

    def selected_items(self):
        items = []
        for field_name, quantity in self.cleaned_data.items():
            if not field_name.startswith('item_') or not quantity:
                continue
            item_id = int(field_name.replace('item_', ''))
            items.append((item_id, quantity))
        return items


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'notes']


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'purchase_number', 'notes']


class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ['inventory_item', 'quantity', 'unit_cost']

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise forms.ValidationError('Quantity must be greater than zero.')
        return quantity

    def clean_unit_cost(self):
        unit_cost = self.cleaned_data['unit_cost']
        if unit_cost < 0:
            raise forms.ValidationError('Unit cost cannot be negative.')
        return unit_cost


class CashDeskEntryForm(forms.ModelForm):
    class Meta:
        model = CashDeskEntry
        fields = ['entry_type', 'amount', 'reason']

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount


class AdminUserCreateForm(UserCreationForm):
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'password1', 'password2']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.pop('autofocus', None)
    def save(self, commit=True):
        user = super().save(commit=commit)
        UserProfile.objects.update_or_create(user=user, defaults={'role': self.cleaned_data['role']})
        return user


class BasePurchaseItemFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        has_line = False
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            if form.cleaned_data.get('inventory_item') and form.cleaned_data.get('quantity'):
                has_line = True
                break
        if not has_line:
            raise forms.ValidationError('Add at least one item to the purchase.')


PurchaseItemFormSet = formset_factory(
    PurchaseItemForm,
    formset=BasePurchaseItemFormSet,
    extra=3,
    can_delete=True,
)
