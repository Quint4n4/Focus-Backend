import uuid

from django.db import models
from django.utils.text import slugify


class Company(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=200)
    slug       = models.SlugField(max_length=100, unique=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering            = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def generate_slug(cls, name: str) -> str:
        base = slugify(name)
        if not base:
            base = 'company'
        slug = base
        n = 1
        while cls.objects.filter(slug=slug).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug
