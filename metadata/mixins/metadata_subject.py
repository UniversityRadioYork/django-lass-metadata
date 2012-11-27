"""In which a mixin that allows attached metadata on a model to be
accessed in a common manner is described.

"""

from django.utils import timezone
from metadata.models.key import MetadataKey


class MetadataView(object):
    """A dictionary view abstraction over the metadata system,
    treating each strand of metadata in a metadata subject as a
    separate key in a dictionary.

    """

    class StrandView(object):
        """An intermediary class that represents a strand of metadata
        as a dictionary.

        """
        def __init__(self, subject, date, strand, inherit_function):
            """
            Initialises the strand view.

            Keyword arguments:
            subject - see MetadataView.__init__
            date - see MetadataView.__init__
            strand - the strand of metadata (for example 'text',
                'images' etc) that this view is operating on
            inherit_function - the function, given a date, strand and
                key, to call if a piece of metadata is missing

            """
            self.subject = subject
            self.date = date
            self.strand = strand
            self.strand_data = self.subject.metadata_strands()[strand]
            self.inherit_function = inherit_function

        def __contains__(self, key):
            """
            Checks to see if the given metadata key is in this
            strand.

            """
            key_id = MetadataKey.get(key).id

            result = self.strand_data.filter(
                key__pk=key_id,
                effective_from__lte=self.date
            ).exists()

            if result is False:
                result = self.inherit_function(
                    self.date,
                    self.strand,
                    key,
                    peek=True
                )
            return result

        def __getitem__(self, key):
            """
            Attempts to get a metadatum in the current
            strand.

            """
            # First let's see if the key actually exists.
            try:
                key_id = MetadataKey.get(key).id
            except MetadataKey.DoesNotExist:
                raise KeyError(
                    'No such metadata key {0}.'.format(key)
                )
            # Now try to get the actual metadata
            try:
                result = self.strand_data.filter(
                    key__pk=key_id,
                    effective_from__lte=self.date
                ).order_by(
                    '-effective_from'
                ).latest().value
            except self.subject.__class__.DoesNotExist:
                # Try inheritance
                result = self.inherit_function(
                    self.date,
                    self.strand,
                    key
                )
            return result

    def __init__(self, subject, date, inherit_function):
        """Initialises the metadata view.

        Keyword arguments:
        subject - the object whose metadata is being presented as a
            dictionary
        date - the date representing the period of time used to
            decide what constitutes "active" metadata
        inherit_function - the function, given a date, strand and
            key, to call if a piece of metadata is missing

        """
        self.subject = subject
        self.date = date
        self.inherit_function = inherit_function

    def __call__(self, date=None):
        """
        Backwards compatibility for any code that calls metadata(),
        or metadata(date).

        New code should use metadata as a field, or call
        metadata_at(date).

        """
        return self if not date else self.__class__(
            self.subject,
            date,
            self.inherit_function
        )

    def __contains__(self, strand):
        """Checks to see if a named strand is present."""
        return (strand in self.subject.metadata_strands())

    def __getitem__(self, strand):
        """Attempts to get a view for a metadata strand."""
        if not self.__contains__(strand):
            raise KeyError('No such metadata strand here.')
        return MetadataView.StrandView(
            self.subject,
            self.date,
            strand,
            self.inherit_function
        )


class MetadataSubjectMixin(object):
    """Mixin granting the ability to access metadata.

    """

    ## MANDATORY OVERRIDES ##

    def metadata_strands(self):
        """
        Returns a dictionary of related sets that provide the
        metadata strands.

        These should usually be organised along type lines, for
        example {'text': textual_metadata_set,
        'images': image_metadata_set, etc...}.

        This should invariably be overridden in mixin users.

        """
        raise NotImplementedError(
            'Must implement metadata_strands.')

    ## OPTIONAL OVERRIDES ##

    def default_inherit_function(self, date, strand, key, peek=False):
        """
        Default inheritance function, which tries to access the
        metadata on this subject's metadata parent, and throws a
        :class:`KeyError` if no parent exists.

        If *peek* is True, the function should instead return True if
        the metadata key exists, and False if otherwise.

        This can be overridden.

        """
        value = None
        value_found = False

        if hasattr(self, 'metadata_parent'):
            if self.metadata_parent():
                met = self.metadata_parent().metadata_at(date)[strand]
                value = (key in met) if peek else met[key]
                value_found = True

        if not value_found:
            raise KeyError(
                'No metadata at {0} in strand {1}:{2} called {3}.'
                .format(date, self, strand, key)
            )
        return value

    def metadata_parent(self):
        """
        Returns an object that metadata should be inherited from
        if not assigned for this object.

        This can return None if no inheriting should be done.

        """
        return None

    ## MAGIC METHODS ##

    def __getattr__(self, name):
        """
        Attribute retrieval hook that intercepts calls for *metadata*
        and reroutes them to *metadata_at*, as well as attempting to
        route calls for items to the first matching metadatum in
        the current strands.

        """
        result = None
        result_def = False

        if name != 'range_start':
            now = (timezone.now()
                   if not hasattr(self, 'range_start')
                   else self.range_start())
            if name == 'metadata':
                result = self.metadata_at(now)
                result_def = True
            elif not name.startswith('_'):
                for strand in self.metadata_strands():
                    md = self.metadata_at(now)[strand]
                    if name in md:
                        result = md[name]
                        result_def = True
                        break

        if not result_def:
            raise AttributeError
        return result

    ## OTHER FUNCTIONS ##

    def metadata_at(self, date, inherit_function=None):
        """
        Returns a dict-like object that allows the strands of
        metadata active on this item at the given time.

        The result is two-tiered and organised first by metadata
        strand and then by key.

        If ``inherit_function`` is specified, it will be supplied
        a date, strand and key in the event that a key is accessed
        that does not appear in the metadata strand for this subject
        on that date, and should return either a metadatum inherited
        by this subject in its place or raise :class:`KeyError`.

        """
        return MetadataView(
            self,
            date,
            (self.default_inherit_function
             if not inherit_function
             else inherit_function)
        )
