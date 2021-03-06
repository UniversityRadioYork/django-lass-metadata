"""Base admin classes for metadata administration."""

from django.contrib import admin


class MetadataAdmin(admin.ModelAdmin):
    """Base class for metadata admin-lets."""

    date_hierarchy = 'effective_from'
    list_display = (
        'element',
        'key',
        'value',
        'creator',
        'approver',
        'effective_from',
        'effective_to',
    )


class GeneralMetadataInline(admin.TabularInline):
    """Base inline class for anything that's like metadata."""

    # Doing this makes the siteadmin virtually unuseable without JS,
    # but closes an annoying bug that causes the extra fields to
    # demand being filled in due to having their times populated.
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Provides a form field for foreign keys.

        Overrides the normal inline so that submitter and approver
        are set, by default, to the currently logged in user.

        """
        is_user_field = (
            db_field.name == 'creator'
            or db_field.name == 'approver'
        )
        if is_user_field:
            kwargs['initial'] = request.user.id
        return super(
            GeneralMetadataInline,
            self
        ).formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )


class MetadataInline(GeneralMetadataInline):
    """Base inline class for metadata inline admin-lets."""

    fields = (
        'key',
        'value',
        'effective_from',
        'effective_to',
        'approver',
        'creator',
    )


class TextMetadataInline(MetadataInline):
    """Specialisation of MetadataInline for text metadata."""

    verbose_name = "associated text item"
    verbose_name_plural = "associated text items"


class ImageMetadataInline(MetadataInline):
    """Specialisation of MetadataInline for image metadata."""

    verbose_name = "associated image"
    verbose_name_plural = "Associated images"


class PackageEntryInline(GeneralMetadataInline):
    """Snap-in for editing package entries inline."""

    verbose_name = "branding package"
    verbose_name_plural = "branding packages"

    fields = (
        'package',
        'effective_from',
        'effective_to',
        'approver',
        'creator',
    )
