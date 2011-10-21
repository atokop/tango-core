"Utilities for internal use within Tango framework."

import code
import imp
import pkgutil
import re


def get_module(name):
    """Get a module given its import name.

    This is particularly useful since Python's imp.find_module does not handle
    hierarchical module names (names containing dots).

    Example:
    >>> get_module('simplesite.stash') # doctest:+ELLIPSIS
    <module 'simplesite.stash' from '...'>
    >>> get_module('simplesite') # doctest:+ELLIPSIS
    <module 'simplesite' from '...'>
    >>> get_module('testsite') # doctest:+ELLIPSIS
    <module 'testsite' from '...'>
    >>> get_module('tango') # doctest:+ELLIPSIS
    <module 'tango' from '...'>
    >>>
    """
    packagename, base = package_submodule(name)
    if packagename is None:
        return __import__(base)
    return getattr(__import__(packagename, fromlist=[base]), base)


def get_module_docstring(filepath):
    """Get module-level docstring of Python module at filepath.

    Get the docstring without running the code in the module, therefore
    avoiding any side-effects in the file. This is particularly useful for
    scripts with docstrings.

    A filepath string is used instead of module object to avoid side-effects.

    Example:
    >>> filepath = find_module_filepath('testsite.stash.index')
    >>> filepath # doctest:+ELLIPSIS
    '.../tests/testsite/stash/index.py'
    >>> print get_module_docstring(filepath).strip()
    site: test
    routes:
     - template:index.html: /
    exports:
     - title: Tango
    >>>

    Example, module without a docstring:
    >>> print get_module_docstring(find_module_filepath('empty'))
    None
    >>>
    """
    co = compile(open(filepath).read(), filepath, 'exec')
    if co.co_consts and isinstance(co.co_consts[0], basestring):
        docstring = co.co_consts[0]
    else:
        docstring = None
    return docstring


def get_module_filepath(module):
    """Get the file path of the given module.

    Example:
    >>> import testsite # a Python package
    >>> import simplest # a single .py module
    >>> get_module_filepath(testsite) # doctest:+ELLIPSIS
    '...tests/testsite'
    >>> 'tests/simplest.py' in get_module_filepath(simplest)
    True
    >>>
    """
    if hasattr(module, '__path__'):
        # A package's __path__ attribute is a list. Use the first element.
        return module.__path__[0]
    else:
        return module.__file__


def find_module_filepath(name):
    """Get filepath of module matching the given name, or None if not found.

    Example:
    >>> find_module_filepath('testsite.stash') # doctest:+ELLIPSIS
    '.../tests/testsite/stash'
    >>> find_module_filepath('testsite.stash.index') # doctest:+ELLIPSIS
    '.../tests/testsite/stash/index.py'
    >>> find_module_filepath('simplest') # doctest:+ELLIPSIS
    '.../tests/simplest.py'
    >>> find_module_filepath('doesnotexist')
    >>>
    """
    try:
        loader = pkgutil.get_loader(name)
    except ImportError:
        return None
    if loader is None:
        return None
    else:
        return loader.filename


def module_exists(name):
    """Return True if a module by the given name exists, or False if not.

    Example:
    >>> module_exists('doesnotexist')
    False
    >>> module_exists('tango')
    True
    >>> module_exists('simplesite')
    True
    >>> module_exists('simplesite.config')
    True
    >>> module_exists('simplest')
    True
    >>> module_exists('simplest.config')
    False
    >>> module_exists('importerror')
    True
    >>> module_exists('testsite.stash.package.module')
    True
    >>> module_exists('testsite.stash.package.doesnotexist')
    False
    >>> module_exists('doesnotexist.module')
    False
    >>>
    """
    # This function must be very careful not to suppress real ImportErrors.
    package, submodule = package_submodule(name)
    if package is None:
        try:
            imp.find_module(name)
        except ImportError:
            return False
        return True

    root = root_package(package)
    try:
        pkg = imp.find_module(root)
    except ImportError:
        return False

    pkg = __import__(root)
    if not module_is_package(pkg):
        return False
    for _, x, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__+'.'):
        if x == name:
            return True
    return False


def name_is_package(name):
    """Return True if import name is for a Python package, or False if not.

    Returns None if the package is not found.

    Example:
    >>> name_is_package('testsite')
    True
    >>> name_is_package('simplest')
    False
    >>> name_is_package('doesnotexist')
    >>>
    """
    loader = pkgutil.get_loader(name)
    if loader is None:
        return None
    # Provides a simpler interface to loader.is_package(fullname).
    # loader.is_package requires fullname argument, even though it isn't used.
    return loader.etc[2] == imp.PKG_DIRECTORY


def module_is_package(module):
    """Return True if module is a Python package, or False if not.

    Example:
    >>> import testsite # a Python package
    >>> import simplest # a single .py module
    >>> module_is_package(testsite)
    True
    >>> module_is_package(simplest)
    False
    >>>
    """
    if hasattr(module, '__path__'):
        return True
    else:
        return False


def package_submodule(hierarchical_module_name):
    """Provide package name, submodule name from dotted module name.

    Example:
    >>> package_submodule('simplesite')
    (None, 'simplesite')
    >>> package_submodule('tango.factory')
    ('tango', 'factory')
    >>> package_submodule('tango')
    (None, 'tango')
    >>> package_submodule('')
    (None, None)
    >>>
    """
    tokens = hierarchical_module_name.split('.')
    return str('.'.join(tokens[:-1])) or None, str(tokens[-1]) or None


def root_package(hierarchical_module_name):
    """Provide the root package name from a dotted module name.

    Example:
    >>> root_package('tango.factory')
    'tango'
    >>> root_package('tango.helpers')
    'tango'
    >>> root_package('testsite')
    'testsite'
    >>> root_package('testsite.stash')
    'testsite'
    >>> root_package('testsite.stash.package')
    'testsite'
    >>> root_package('testsite.stash.package.module')
    'testsite'
    >>>
    """
    return hierarchical_module_name.split('.')[0]


def url_parameter_match(route, parameter):
    """Determine whether a route contains a url parameter, return True if so.

    Example:
    >>> url_parameter_match('/<argument>', 'argument')
    True
    >>> url_parameter_match('/<argument>/', 'argument')
    True
    >>> url_parameter_match('/<int:argument>', 'argument')
    True
    >>> url_parameter_match('/int:<argument>/', 'argument')
    True
    >>> url_parameter_match('/path:<argument>/', 'argument')
    True
    >>> url_parameter_match('/path/to/<parameter>/', 'parameter')
    True
    >>> url_parameter_match('/path/to/<path:parameter>/', 'parameter')
    True
    >>> url_parameter_match('/path/to/<aparameter>/', 'parameter')
    False
    >>> url_parameter_match('/path/to/<path:aparameter>/', 'parameter')
    False
    >>> url_parameter_match('/', 'parameter')
    False
    >>>
    """
    return re.search('[<:]{0}>'.format(parameter), route) is not None
