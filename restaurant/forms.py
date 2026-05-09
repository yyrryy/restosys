from django import forms
from django.contrib.auth import get_user_model

from .models import DiningTable, InventoryItem, MenuItem, RecipeComponent, UserProfile


class DiningTableForm(forms.ModelForm):
    class Meta:
        model = DiningTable
        fields = ['name', 'seats', 'status']


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['name', 'category', 'price', 'image', 'is_available']
        labels = {
            'image': 'Image',
        }


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'quantity', 'unit', 'reorder_level']


class RecipeComponentForm(forms.ModelForm):
    class Meta:
        model = RecipeComponent
        fields = ['menu_item', 'inventory_item', 'quantity']


class OrderCreateForm(forms.Form):
    table = forms.ModelChoiceField(queryset=DiningTable.objects.none())
    customer_name = forms.CharField(max_length=120, required=False)

    def __init__(self, *args, **kwargs):
        menu_items = kwargs.pop('menu_items')
        require_table = kwargs.pop('require_table', True)
        include_waiter_choice = kwargs.pop('include_waiter_choice', False)
        super().__init__(*args, **kwargs)
        self.fields['table'].queryset = DiningTable.objects.all()
        self.fields['table'].required = require_table

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
