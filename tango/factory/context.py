"Marshal template contexts exported declaratively by Tango content packages."

import copy
import pkgutil

import yaml

from tango.helpers import get_module


HINT_DELIMITER = '<-'


def build_package_context(package):
    """Pull contexts from site package, discovering modules & parsing headers.

    Structure of site context:

    site_context = {'site': {'route1': {}, 'route2': {}, 'routeN': {}}}
    site_context['site']['routeN'] is a standard template context dict.

    >>> import testsite.content
    >>> build_package_context(testsite.content)
    ... # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    {'test':
     {'/route1': {'count': 2, 'name': '...', 'sequence': [4, 5, 6]},
      '/route2': {'count': 2, 'name': '...', 'sequence': [4, 5, 6]},
      '/files/page-<parameter>.html':
       {'_routing': {'parameter': [0, 1, 2]}, 'purpose': '...'},
      '/': {'project': 'tango', 'hint': '...', 'title': 'Tango'},
      '/routing/<parameter>/':
       {'_routing': {'parameter': [0, 1, 2]}, 'purpose': '...'},
      '/another/<argument>/':
       {'_routing': {'argument': xrange(3, 6)}, 'purpose': '...'}}}
    >>>

    :param package: Tango site content package object
    :type package: module
    """
    package_context = {}

    for module in discover_modules(package):
        context = pull_context(module)
        if context is None:
            continue
        for site in context:
            site_context = package_context.get(site, {})
            for route in context[site]:
                route_context = site_context.get(route, {})
                # TODO: Warn on route context overwrite.
                route_context.update(context[site][route])
                site_context[route] = route_context
            package_context[site] = site_context
    return package_context


def discover_modules(package):
    """Discover content package modules, returning iterable of module objects.

    This searches all subpackages and includes __init__ modules.

    Example:
    >>> import testsite.content
    >>> discover_modules(testsite.content) # doctest:+ELLIPSIS
    <generator object discover_modules at 0x...>
    >>> list(discover_modules(testsite.content))
    ... # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    [<module 'testsite.content' from '...'>,
     <module 'testsite.content.index' from '...'>,
     <module 'testsite.content.multiple' from '...'>,
     <module 'testsite.content.package' from '...'>,
     <module 'testsite.content.package.module' from '...'>]
    >>>

    :param package: Tango site content package object
    :type package: module
    """
    path = package.__path__
    prefix = package.__name__ + '.'
    onerror = lambda args: None
    yield package
    for _, name, _ in pkgutil.walk_packages(path, prefix, onerror):
        yield get_module(name)


def pull_context(module):
    """Pull dict template context from module, parsing it's header.

    Example:
    >>> from testsite.content import index, multiple
    >>> pull_context(index)
    {'test': {'/': {'title': 'Tango'}}}
    >>> pull_context(multiple) # doctest:+NORMALIZE_WHITESPACE
    {'test': {'/route1': {'count': 2, 'name': 'multiple.py context',
     'sequence': [4, 5, 6]}, '/route2': {'count': 2, 'name':
     'multiple.py context', 'sequence': [4, 5, 6]}}}
    >>> from testsite.content import routing
    >>> pull_context(routing)
    ... # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    {'test': {'/files/page-<parameter>.html':
     {'_routing': {'parameter': [0, 1, 2]}, 'purpose': '...'},
     '/routing/<parameter>/':
     {'_routing': {'parameter': [0, 1, 2]}, 'purpose': '...'},
     '/another/<argument>/':
     {'_routing': {'argument': xrange(3, 6)}, 'purpose': '...'}}}
    >>>

    :param module: Tango site content package module object
    :type module: module
    """
    header = parse_header(module)
    if header is None:
        return None

    base_route_context = {}
    for name in header['exports']:
        if name in header['static']:
            base_route_context[name] = header['exports'][name]
        else:
            base_route_context[name] = getattr(module, name)

    routing = {}
    for lookup in header.get('_routing', []):
        for name, iterable_name in lookup.items():
            routing[name] = getattr(module, iterable_name)
            if hasattr(routing[name], '__call__'):
                routing[name] = routing[name]()

    site_context = {}
    for route in header['routes']:
        route_context = copy.deepcopy(base_route_context)
        local_routing = {}
        for argument in routing.keys():
            # TODO: Support URL converters. (Basico)
            if ('<%s>' % argument) in route:
                local_routing[argument] = routing[argument]
        if local_routing:
            route_context['_routing'] = local_routing
        else:
            route_context.pop('_routing', None)

        # routing here, match route with routing path?
        site_context[route] = route_context

    return {header['site']: site_context}


def parse_header(module):
    """Parse module header for template context metadata.

    Modules in the site content package must have these fields in the header:

    * site
    * routes
    * exports

    Raise KeyError if any of these fields are missing.

    Example:
    >>> from testsite.content import index, multiple
    >>> parse_header(index) # doctest:+NORMALIZE_WHITESPACE
    {'routes': ['/'], 'exports': {'title': 'Tango'},
     'static': ['title'], 'site': 'test'}
    >>> header = parse_header(multiple)
    >>> header['site']
    'test'
    >>> header['routes']
    ['/route1', '/route2']
    >>> header['exports']
    {'count': 'number', 'name': 'string', 'sequence': '[number]'}
    >>> from testsite.content.package import module
    >>> parse_header(module)
    {'routes': ['/'], 'exports': {'hint': None}, 'static': [], 'site': 'test'}
    >>> from testsite.content import routing
    >>> parse_header(routing)
    ... # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    {'routes': ['/routing/<parameter>/', '/another/<argument>/',
                '/files/page-<parameter>.html'],
     'exports': {'purpose': '...'},
    '_routing': [{'parameter': 'parameters'}, {'argument': 'arguments'}],
    'static': ['purpose'], 'site': 'test'}
    >>>

    :param module: Tango site content package module object
    :type module: module
    """
    try:
        rawheader = yaml.load(module.__doc__)
    except yaml.scanner.ScannerError:
        # TODO: Warn about failed parse here, reporting module.__name__.
        return None
    except AttributeError:
        # Not an error or a warning, just a module without a docstring.
        return None

    if not isinstance(rawheader, dict):
        # module has a docstring, but it's not yaml.
        return None

    header = {'site': rawheader['site']}
    routing = rawheader.get('routing')
    if routing is not None:
        header['_routing'] = routing

    if isinstance(rawheader['routes'], basestring):
        header['routes'] = [rawheader['routes']]
    else:
        header['routes'] = list(rawheader['routes'])
        # TODO: Warn about duplicates here, reporting module.__name__.

    header['exports'] = {}
    header['static'] = []
    if isinstance(rawheader['exports'], basestring):
        rawexport = [rawheader['exports']]
    else:
        rawexport = list(rawheader['exports'])
    for exportstmt in rawexport:
        # TODO: Warn about duplicates here, reporting module.__name__.
        if isinstance(exportstmt, basestring):
            tokens = exportstmt.split(HINT_DELIMITER)
            name = tokens[0].strip()
            if len(tokens) > 1:
                hint = HINT_DELIMITER.join(tokens[1:]).strip()
                header['exports'][name] = hint
            else:
                header['exports'][name] = None
        else:
            for name in exportstmt:
                header['exports'][name] = exportstmt[name]
                header['static'].append(name)
    return header
