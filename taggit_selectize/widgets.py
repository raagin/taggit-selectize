from django import forms
import six
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType

from taggit.utils import edit_string_for_tags

from .conf import settings

from django.urls import reverse


def bool_or_str(val):
   if val == True:
      return 'true'
   elif val == False:
      return 'false'
   return val

class TagSelectize(forms.TextInput):
    def __init__(self, *args, **kwargs):
        through = kwargs.pop('through')
        self.tag_content_type_id = None
        if through:
            tag_model = through.tag.field.related_model
            tag_content_type = ContentType.objects.get_for_model(tag_model)
            self.tag_content_type_id = tag_content_type.id
        super(TagSelectize, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        if value is not None and not isinstance(value, six.string_types):
            value = edit_string_for_tags(value)

        if hasattr(self, 'allow_create'):
            allow_create = self.allow_create
        else: 
            allow_create = settings.TAGGIT_SELECTIZE['CREATE']

        html = super(TagSelectize, self).render(name, value, attrs, renderer)

        js_plugins = []
        if settings.TAGGIT_SELECTIZE['REMOVE_BUTTON']:
            js_plugins.append("remove_button")
        if settings.TAGGIT_SELECTIZE['RESTORE_ON_BACKSPACE']:
            js_plugins.append("restore_on_backspace")
        if settings.TAGGIT_SELECTIZE['DRAG_DROP']:
            js_plugins.append("drag_drop")

        js = u"""
            <script type="text/javascript">
                (function($) {
                    $(document).ready(function() {
                        $("input[id=%(id)s]").selectize({
                            valueField: 'name',
                            labelField: 'name',
                            searchField: 'name',
                            diacritics: %(diacritics)s,
                            create: %(create)s,
                            persist: %(persist)s,
                            openOnFocus: %(open_on_focus)s,
                            hideSelected: %(hide_selected)s,
                            closeAfterSelect: %(close_after_select)s,
                            loadThrottle: %(load_throttle)d,
                            preload: %(preload)s,
                            addPrecedence: %(add_precedence)s,
                            selectOnTab: %(select_on_tab)s,
                            delimiter: '%(delimiter)s',
                            plugins: [%(plugins)s],
                            render: {
                                option: function(item, escape) {
                                    return '<div>' +
                                        '<span class="title">' +
                                            '<span class="name">' + escape(item.name) + '</span>' +
                                        '</span>' +
                                    '</div>';
                                },
                                'item': function(item, escape) {
                                    name = item.name.replace(/^\s*"|"\s*$/g, '');
                                    return '<div class="item">' + escape(name) + '</div>';
                                }
                            },
                            load: function(query, callback) {
                                if (query.length < %(minimum_query_length)d) return callback();
                                $.ajax({
                                    url: '%(remote_url)s?query=' + encodeURIComponent(query) + '%(tag_content_type)s',
                                    type: 'GET',
                                    error: function() {
                                        callback();
                                    },
                                    success: function(res) {
                                        callback(res.tags.slice(0, %(recommendation_limit)s));
                                    }
                                });
                            }
                        }).parents('.form-row').css('overflow', 'visible');
                    });
                })(%(jquery)s || jQuery || django.jQuery);
            </script>
        """ % {
            'id': attrs['id'],
            'minimum_query_length': settings.TAGGIT_SELECTIZE['MINIMUM_QUERY_LENGTH'],
            'recommendation_limit': settings.TAGGIT_SELECTIZE['RECOMMENDATION_LIMIT'],
            'diacritics': "true" if settings.TAGGIT_SELECTIZE['DIACRITICS'] else "false",
            'create': bool_or_str(allow_create),
            'persist': "true" if settings.TAGGIT_SELECTIZE['PERSIST'] else "false",
            'open_on_focus': "true" if settings.TAGGIT_SELECTIZE['OPEN_ON_FOCUS'] else "false",
            'hide_selected': "true" if settings.TAGGIT_SELECTIZE['HIDE_SELECTED'] else "false",
            'close_after_select': "true" if settings.TAGGIT_SELECTIZE['CREATE'] else "false",
            'load_throttle': settings.TAGGIT_SELECTIZE['LOAD_THROTTLE'],
            'preload': bool_or_str(settings.TAGGIT_SELECTIZE['PRELOAD']),
            'add_precedence': "true" if settings.TAGGIT_SELECTIZE['ADD_PRECEDENCE'] else "false",
            'select_on_tab': "true" if settings.TAGGIT_SELECTIZE['SELECT_ON_TAB'] else "false",
            'delimiter': settings.TAGGIT_SELECTIZE['DELIMITER'],
            'plugins': ",".join(["\"{}\"".format(plugin) for plugin in js_plugins]),
            'remote_url': reverse('tags_recommendation'),
            'tag_content_type': '&tag_content_type_id=%s' % self.tag_content_type_id if self.tag_content_type_id else '',
            'jquery': settings.TAGGIT_SELECTIZE_JQUERY if hasattr(settings, 'TAGGIT_SELECTIZE_JQUERY') else 'false'
        }
        return mark_safe("\n".join([html, js]))

    class Media:
        css = {
            'all': settings.TAGGIT_SELECTIZE['CSS_FILENAMES']
        }
        js = settings.TAGGIT_SELECTIZE['JS_FILENAMES']
