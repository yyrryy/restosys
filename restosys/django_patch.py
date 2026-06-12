"""
Patch for Django 4.2 compatibility with Python 3.14.
Fixes AttributeError in template context copying.
"""
import sys
import copy as copy_module

if sys.version_info >= (3, 14):
    from django.template.context import BaseContext
    
    def patched_copy(self):
        """Fixed __copy__ that works with Python 3.14"""
        # Create a new instance without calling __init__
        duplicate = self.__class__.__new__(self.__class__)
        # Copy dict attributes manually
        for key, value in self.__dict__.items():
            setattr(duplicate, key, copy_module.copy(value) if isinstance(value, list) else value)
        return duplicate
    
    BaseContext.__copy__ = patched_copy
