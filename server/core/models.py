#server/core/models.py
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """Custom queryset with soft delete methods"""
    
    def delete(self):
        """Soft delete all objects in queryset"""
        return super().update(deleted_at=timezone.now())
    
    def hard_delete(self):
        """Permanently delete all objects in queryset"""
        return super().delete()
    
    def alive(self):
        """Return only non-deleted objects"""
        return self.filter(deleted_at__isnull=True)
    
    def deleted(self):
        """Return only deleted objects"""
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted objects by default"""
    
    def __init__(self, *args, **kwargs):
        self.alive_only = kwargs.pop('alive_only', True)
        super().__init__(*args, **kwargs)
    
    def get_queryset(self):
        if self.alive_only:
            return SoftDeleteQuerySet(self.model).filter(deleted_at__isnull=True)
        return SoftDeleteQuerySet(self.model)
    
    def hard_delete(self):
        return self.get_queryset().hard_delete()


class SoftDeleteModel(models.Model):
    """
    Base model with soft delete functionality.
    
    Usage:
        class Product(SoftDeleteModel):
            name = models.CharField(max_length=100)
        
        Soft delete (keeps in database)
        product.delete()
        
        Hard delete (removes from database)
        product.delete(hard=True)
        product.hard_delete()
        
        Restore soft-deleted object
        product.restore()
        
        Query only non-deleted
        Product.objects.all()  # Returns alive objects
        
        Query including deleted
        Product.all_objects.all()  # Returns all objects
        
        Query only deleted
        Product.objects.deleted()
    """
    
    deleted_at = models.DateTimeField(
        null=True, 
        blank=True, 
        editable=False,
        db_index=True,
        help_text="Timestamp when this record was soft-deleted"
    )
    
    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(alive_only=False)
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False, hard=False):
        """
        Soft delete by default. Use hard=True for permanent deletion.
        
        Args:
            using: Database alias
            keep_parents: Whether to keep parent objects
            hard: If True, permanently delete from database
        """
        if hard:
            super().delete(using=using, keep_parents=keep_parents)
        else:
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])
    
    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete from database"""
        super().delete(using=using, keep_parents=keep_parents)
    
    def restore(self):
        """Restore a soft-deleted record"""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
    
    @property
    def is_deleted(self):
        """Check if record is soft-deleted"""
        return self.deleted_at is not None
