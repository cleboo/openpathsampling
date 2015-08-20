import yaml
import types

import numpy as np

import logging

from openpathsampling.tools import WeakLimitCache


logger = logging.getLogger(__name__)
init_log = logging.getLogger('openpathsampling.initialization')


class ObjectStore(object):
    """
    Base Class for storing complex objects in a netCDF4 file. It holds a
    reference to the store file.
    """

    allowed_types = [
        'int', 'float', 'long', 'str', 'bool'
        'nunpy.float32', 'numpy.float64',
        'numpy.int8', 'numpy.inf16', 'numpy.int32', 'numpy.int64',
        'numpy.uint8', 'numpy.uinf16', 'numpy.uint32', 'numpy.uint64',
        'index', 'length'
    ]

    class DictDelegator(object):
        def __init__(self, store, dct):
            self.prefix = store.prefix + '_'
            self.dct = dct

        def __getitem__(self, item):
#            print self.dct.keys()
            return self.dct[self.prefix + item]

    def prefix_delegate(self, dct):
        return ObjectStore.DictDelegator(self, dct)

    default_cache = 10000

    def __init__(self, content_class, has_uid=False, json=True,
                 caching=None, load_partial=False,
                nestable=False, has_name=False):

        """

        Parameters
        ----------
        storage
        content_class
        has_uid
        json
        dimension_units
        caching : dict-like or bool or int or None
            this is the dict used for caching.
            `True` means to use a python built-in dict which unlimited caching.
            Be careful.
            `False` means no caching at all. If a dict-like object is passed,
            it will be used.
            An integer `n` means to use LRU Caching with maximal n elements and is
            equal to `cache=LRUCache(n)`
            Default (None) is equivalent to `cache=ObjectStore.default_cache`
        load_partial : bool
            if this is set to `True` the storage allows support for partial
            delayed loading of member variables. This is useful for larger
            objects that might only be required in particular circumstances.
            (default is `False`)
        nestable : bool
            if true this marks the content_class to be saved as nested dict
            objects and not a pointing to saved objects. So the saved complex
            object is only stored once and not split into several objects that
            are referenced by each other in a tree-like fashion

        Notes
        -----
        Usually you want caching, but limited. Recommended is to use an LRUCache
        with a reasonable number that depends on the typical number of objects to
        cache and their size

        Attributes
        ----------

        storage : Storage
            the reference the Storage object where all data is stored
        content_class : class
            a reference to the class type to be stored using this Storage
        has_uid : bool
            if `True` objects can also be loaded by a string identifier/name
        json : string
            if already computed a JSON Serialized string of the object
        simplifier : util.StorableObjectJSON
            an instance of a JSON Serializer
        identifier : str
            name of the netCDF variable that contains the string to be
            identified by. So far this is `name`
        cache : dict-like (int or str : object)
            a dictionary that holds references to all stored elements by index
            or string for named objects. This is only used for cached access
            if caching is not `False`

        Notes
        -----
        The class that takes care of storing data in a file is called a Storage,
        so the netCDF subclassed Storage is a storage. The classes that know how
        to load and save an object from the storage are called stores,
        like ObjectStore, SampleStore, etc...

        """

        self._storage = None
        self.content_class = content_class
        self.prefix = None
        self.cache = dict()
        self.has_uid = has_uid
        self.has_name = has_name
        self.json = json
        self._free = set()
        self._cached_all = False
        self._names_loaded = False
        self.nestable = nestable
        self.name_idx = dict()

        self.variables = dict()
        self.vars = dict()
        self.units = dict()

        # First, apply standard decorator for loading and saving
        # this handles all the setting and getting of .idx and is
        # always necessary!

        if load_partial:
            # this allows the class to load members only if needed
            # adds a different __getattr__ to the content class
            # makes only sense if not already lazy loading
            # it uses load_constructor instead to create an empty object
            # and then each class can attach delayed loaders to load
            # when necessary, fall back is of course the normal load function

            if hasattr(self, 'load_empty'):
                cls = self.content_class

                def _getattr(this, item):
                    if item == '_idx':
                        return this.__dict__['idx']

                    if hasattr(cls, '_delayed_loading'):
                        if item in dir(cls):
                            return object.__getattribute__(this, item)

                        if item in cls._delayed_loading:
                            _loader = cls._delayed_loading[item]
#                            print 'from', repr(self.storage), id(self), 'and not', repr(this), 'load', item
                            _loader(this)
                        else:
                            raise KeyError(item)

                    return this.__dict__[item]

                setattr(cls, '__getattr__', _getattr)

                _load = self.load
                self.load = types.MethodType(loadpartial(_load), self)

        _save = self.save
        self.save = types.MethodType(saveidx(_save), self)

        _load = self.load
        self.load = types.MethodType(loadidx(_load), self)

        if caching is not False:
            # wrap load/save to make this work. I use MethodType here to bind the
            # wrapped function to this instance. An alternative would be to
            # add the wrapper to the class itself, which would mean that all
            # instances have the same setting and a change would be present in all
            # instances. E.g., first instance has caching and the second not
            # when the second instance is created the change in the class would
            # also disable caching in the first instance. The present way with
            # bound methods is more flexible
            # Should be not really important, since there will be mostly only one
            # storage, but this way it is cleaner

            _save = self.save
            self.save = types.MethodType(savecache(_save), self)

            _load = self.load
            self.load = types.MethodType(loadcache(_load), self)

    def register(self, storage, name):
        self._storage = storage
        self.prefix = name

        self.variables = self.prefix_delegate(self.storage.variables)
        self.units = self.prefix_delegate(self.storage.units)
        self.vars = self.prefix_delegate(self.storage.vars)

    @property
    def identifier(self):
        return self.prefix + '_uid'

    @property
    def storage(self):
        if self._storage is None:
            raise RuntimeError('A store need to be added to a storage to be used!')

        return self._storage

    @property
    def dimension_units(self):
        return self.storage.dimension_units

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "store.%s[%s]" % (
            self.prefix, self.content_class.__name__)

    @property
    def simplifier(self):
        return self.storage.simplifier

    def set_caching(self, caching):
        if caching is None:
            caching = self.default_cache

        if caching is True:
            self.cache = WeakLimitCache(1000000)
        elif isinstance(caching, dict):
            self.cache = caching

    def idx(self, obj):
        """
        Return the index in this store for a given object

        Parameters
        ----------
        obj : object
            the object that can be stored in this store for which its index is
            to be returned

        Returns
        -------
        int or None
            The integer index of the given object or None if it is not stored yet
        """
        if hasattr(obj, 'idx'):
            if self in obj.idx:
                return obj.idx[self]

        return None

    def set_variable_partial_loading(self, variable, loader=None):
        cls = self.content_class
        if not hasattr(cls, '_delayed_loading'):
            cls._delayed_loading = dict()

        if loader is None:
            loader = func_update_variable(variable, variable)

        cls._delayed_loading[variable] = loader

    def idx_by_name(self, needle):
        """
        Return the index for the (first) object with a given name from the store

        Parameters
        ----------
        needle : str
            The name of the object to be found in the storage

        Returns
        -------
        int or None
            The index of the first found object. If the name is not present,
            None is returned

        Notes
        -----
        Can only be applied to named storages.
        """
        if self.has_uid:
            # if we need a cache we might find the index in there
            if needle in self.cache:
                if type(self.cache[needle]) is int:
                    return self.cache[needle]
                else:
                    return self.cache[needle].idx[self]

            # otherwise search the storage for the name
            found_idx = [ idx for idx,s in enumerate(self.storage.variables[
                self.identifier][:]) if s == needle
            ]

            if len(found_idx) > 0:
                    return found_idx[0]

            return None
        else:
            raise ValueError('Cannot search for name (str) in non-named objects')

    def update_name_cache(self):
        """
        Update the internal cache with all stored names in the store.
        This allows to load by name for named objects
        """
        if self.has_name:
            if not self._names_loaded:
                for idx, name in enumerate(self.storage.variables[self.prefix + "_name"][:]):
                    self._update_name_in_cache(name, idx)

                self._names_loaded = True

    def _update_name_in_cache(self, name, idx):
        if name != '':
            if name not in self.cache:
                self.name_idx[name] = [idx]
            else:
                if idx not in self.cache[name]:
                    self.name_idx[name].append(idx)

    def find(self, name):
        """
        Return all objects with a given name

        Parameters
        ----------
        name : str
            the name to be searched for

        Returns
        -------
        list of objects
            a list of found objects, can be empty [] if no objects with
            that name exist

        """
        if self.has_name:
            if name not in self.name_idx:
                self.update_name_cache()

            return self[self.name_idx[name]]

        return []

    def find_indices(self, name):
        """
        Return indices for all objects with a given name

        Parameters
        ----------
        name : str
            the name to be searched for

        Returns
        -------
        list of int
            a list of indices in the storage for all found objects,
            can be empty [] if no objects with that name exist

        """
        if self.has_name:
            if name not in self.name_idx:
                self.update_name_cache()

            return self.name_idx[name]

        return []


    def find_first(self, name):
        """
        Return first object with a given name

        Parameters
        ----------
        name : str
            the name to be searched for

        Returns
        -------
        object of None
            the first found object, can be None if no object with the given
            name exists

        """
        if self.has_name:
            if name not in self.name_idx:
                self.update_name_cache()

            if len(self.name_idx[name]) > 0:
                return self[self.name_idx[name][0]]

        return None


    def __iter__(self):
        """
        Add iteration over all elements in the storage
        """
        return self.iterator()

    def __len__(self):
        """
        Return the number of stored objects

        Returns
        -------
        int
            number of stored objects

        Notes
        -----
        Equal to `store.count()`
        """
        return self.count()

    def iterator(this, iter_range = None):
        """
        Return an iterator over all objects in the storage

        Parameters
        ----------
        iter_range : slice or None
            if this is not `None` it confines the iterator to objects specified
            in the slice

        Returns
        -------
        Iterator()
            The iterator that iterates the objects in the store

        """
        class ObjectIterator:
            def __init__(self):
                self.storage = this
                self.iter_range = iter_range
                if iter_range is None:
                    self.idx = 0
                    self.end = self.storage.count()
                else:
                    self.idx = iter_range.start
                    self.end = iter_range.stop

            def __iter__(self):
                return self

            def next(self):
                if self.idx < self.end:
                    obj = self.storage.load(self.idx)
                    if self.iter_range is not None and self.iter_range.step is not None:
                        self.idx += self.iter_range.step
                    else:
                        self.idx += 1
                    return obj
                else:
                    raise StopIteration()

        return ObjectIterator()

    def __getitem__(self, item):
        """
        Enable numpy style selection of object in the store
        """
        try:
            if type(item) is int or type(item) is str:
                return self.load(item)
            elif type(item) is slice:
                return [self.load(idx) for idx in range(*item.indices(len(self)))]
            elif type(item) is list:
                return [self.load(idx) for idx in item]
            elif item is Ellipsis:
                return self.iterator()
        except KeyError:
            return None

    def load(self, idx):
        '''
        Returns an object from the storage. Needs to be implemented from
        the specific storage class.

        Parameters
        ----------
        idx : int or str
            either the integer index of the object to be loaded or a string
            (name) for named objects. This will always return the first object
            found with the specified name.

        Returns
        -------
        object
            the loaded object
        '''

        return self.load_json(self.prefix + '_json', idx)

    def clear_cache(self):
        """Clear the cache and force reloading

        """

        self.cache = dict()
        self._cached_all = False

    def cache_all(self):
        """Load all samples as fast as possible into the cache

        """
        if not self._cached_all:
            idxs = range(len(self))
            jsons = self.storage.variables[self.prefix + '_json'][:]

            [ self.add_single_to_cache(i,j) for i,j in zip(
                idxs,
                jsons) ]

            self._cached_all = True

    def add_single_to_cache(self, idx, json):
        """
        Add a single object to cache by json
        """

        if idx not in self.cache:
            simplified = yaml.load(json)
            obj = self.simplifier.build(simplified)

            obj.json = json
            obj.idx[self] = idx

            self.cache[idx] = obj

            if self.has_name:
                name = self.storage.variables[self.prefix + '_name'][idx]
                setattr(obj, '_name', name)
                if name != '':
                    self._update_name_in_cache(obj._name, idx)

            if self.has_uid:
                if not hasattr(obj, '_uid'):
                    # get the name of the object
                    setattr(obj, '_uid', self.get_uid(idx))

    def save(self, obj, idx=None):
        """
        Saves an object to the storage.

        Parameters
        ----------
        obj : object
            the object to be stored
        idx : int or string or `None`
            the index to be used for storing. This is highly discouraged since
            it changes an immutable object (at least in the storage). It is
            better to store also the new object and just ignore the
            previously stored one.

        """

        if self.has_uid and hasattr(obj, '_uid'):
            self.storage.variables[self.identifier][idx] = obj._uid

        self.save_json(self.prefix + '_json', idx, obj)

    def get_uid(self, idx):
        """
        Return the name of and object with given integer index

        Parameters
        ----------
        idx : int
            the integer index of the object whose name is to be returned

        Returns
        -------
        str or None
            Returns the name of the object for named objects. None otherwise.

        """
        if self.has_uid:
            return self.storage.variables[self.identifier][idx]
        else:
            return None

    def get(self, indices):
        """
        Returns a list of objects from the given list of indices

        Parameters
        ----------
        indices : list of int
            the list of integers specifying the object to be returned

        Returns
        -------
        list of objects
            a list of objects stored under the given indices

        """
        return [self.load(idx) for idx in range(0, self.count())[indices]]

    def last(self):
        '''
        Returns the last generated trajectory. Useful to continue a run.

        Returns
        -------
        Trajectoy
            the actual trajectory object
        '''
        return self.load(self.count() - 1)

    def first(self):
        '''
        Returns the last stored object. Useful to continue a run.

        Returns
        -------
        Object
            the actual last stored object
        '''
        return self.load(0)

    def count(self):
        '''
        Return the number of objects in the storage

        Returns
        -------
        number : int
            number of objects in the storage.

        Notes
        -----
        Use len(store) instead
        '''
        return int(len(self.storage.dimensions[self.prefix]))

    def free(self):
        '''
        Return the number of the next free index

        Returns
        -------
        index : int
            the number of the next free index in the storage.
            Used to store a new object.
        '''
        count = self.count()
        self._free = set([ idx for idx in self._free if idx >= count])
        idx = count
        while idx in self._free:
            idx += 1

        return idx

    def reserve_idx(self, idx):
        '''
        Locks an idx as used
        '''
        self._free.add(idx)


    def _init(self):
        """
        Initialize the associated storage to allow for object storage. Mainly
        creates an index dimension with the name of the object.

        Parameters
        ----------
        units : dict of {str : simtk.unit.Unit} or None
            representing a dict of string representing a dimension
            ('length', 'velocity', 'energy') pointing to
            the simtk.unit.Unit to be used. If not None overrides the standard
            units used in the storage
        """
        # define dimensions used for the specific object
        self.storage.createDimension(self.prefix, 0)

        if self.has_uid:
            self.init_variable("uid", 'str',
                description='A unique identifier',
                chunksizes=tuple([10240]))

        if self.has_name:
            self.init_variable("name", 'str',
                description='A name',
                chunksizes=tuple([10240]))

        if self.json:
            self.init_variable("json", 'str',
                description='A json serialized version of the object',
                chunksizes=tuple([10240]))

#==============================================================================
# INITIALISATION UTILITY FUNCTIONS
#==============================================================================

    @staticmethod
    def find_number_type(instance):
        ty = type(instance)

        types = [
            float, int, bool, str, long
        ]

        if ty in types:
            return types[ty].__name__
        elif ty is np.dtype:
            return 'numpy.' + instance.dtype.type.__name__

    @staticmethod
    def _parse_var_type_as_np_type(var_type):
        nc_type = var_type
        if var_type == 'float':
            nc_type = np.float32   # 32-bit float
        elif var_type == 'int':
            nc_type = np.int32   # 32-bit signed integer
        elif var_type == 'index':
            nc_type = np.int32
            # 32-bit signed integer / for indices / -1 : no index (None)
        elif var_type == 'length':
            nc_type = np.int32
            # 32-bit signed integer / for indices / -1 : no length specified (None)
        elif var_type == 'bool':
            nc_type = np.uint8   # 8-bit signed integer for boolean
        elif var_type == 'str':
            nc_type = 'str'

        types = {
            'float' : np.float32,
            'int' : np.int32,
            'index' : np.int32,
            'length' : np.int32,
            'bool' : np.uint8,
            'str' : 'str',
        }

        return types[var_type]

    def init_variable(self, name, var_type, dimensions = None, units=None,
                      description=None, variable_length=False, chunksizes=None):
        '''
        Create a new variable in the netCDF storage. This is just a helper
        function to structure the code better.

        Parameters
        ==========
        name : str
            The name of the variable to be created
        var_type : str
            The string representing the type of the data stored in the variable.
            Allowed are strings of native python types in which case the variables
            will be treated as python or a string of the form 'numpy.type' which
            will refer to the numpy data types. Numpy is preferred sinec the api
            to netCDF uses numpy and thus it is faster. Possible input strings are
            `int`, `float`, `long`, `str`, `numpy.float32`, `numpy.float64`,
            `numpy.int8`, `numpy.int16`, `numpy.int32`, `numpy.int64`
        dimensions : str or tuple of str
            A tuple representing the dimensions used for the netcdf variable.
            If not specified then the default dimension of the storage is used.
        units : str
            A string representing the units used if the var_type is `float`
            the units is set to `none`
        description : str
            A string describing the variable in a readable form.
        variable_length : bool
            If true the variable is treated as a variable length (list) of the
            given type. A built-in example for this type is a string which is
            a variable length of char. This make using all the mixed
            stuff superfluous
        chunksizes : tuple of int
            A tuple of ints per number of dimensions. This specifies in what
            block sizes a variable is stored. Usually for object related stuff
            we want to store everything of one object at once so this is often
            (1, ..., ...)
        '''

        if dimensions is None:
            dimensions = self.prefix

        self.storage.create_variable(
            self.prefix + '_' + name,
            var_type=var_type,
            dimensions=dimensions,
            units=units,
            description=description,
            variable_length=variable_length,
            chunksizes=chunksizes
        )


#==============================================================================
# LOAD / SAVE UTILITY FUNCTIONS
#==============================================================================

    def load_variable(self, name, idx):
        """
        Wrapper for netCDF storage.variables[name][idx] property

        Parameters
        ----------
        name : str
            The name of the variable
        idx : int, slice, list of int, etc...
            An index specification as in netCDF4

        Returns
        -------
        numpy.ndarray
            The data stored in the netCDF variable

        """
        return self.storage.variables[name][idx]

    def save_variable(self, name, idx, value):
        """
        Wrapper for netCDF storage.variables[name][idx] property

        Parameters
        ----------
        name : str
            The name of the variable
        idx : int, slice, list of int, etc...
            An index specification as in netCDF4
        value : numpy.ndarray
            The array to be stored in the variable

        """
        self.storage.variables[name][idx] = value

    def load_json(self, name, idx):
        """
        Load an object from the associated storage using json

        Parameters
        ----------
        name : str
            the name of the variable in the netCDF storage
        idx : int
            the integer index in the variable

        Returns
        -------
        object
            the loaded object

        """
        # TODO: Add logging here
        idx = int(idx)

        json_string = self.storage.variables[name][idx]

        simplified = yaml.load(json_string)
        obj = self.simplifier.build(simplified)
        setattr(obj, 'json', json_string)

        return obj

    def save_json(self, name, idx, obj):
        """
        Save an object as a json string in a variable in the referenced storage

        Parameters
        ----------
        name : str
            the name of the variable in the netCDF storage
        idx : int
            the integer index in the variable
        obj : object
            the object to be stored as JSON

        """
        if not hasattr(obj,'json'):
            setattr(obj, 'json', self.object_to_json(obj))

        self.storage.variables[name][idx] = obj.json


#==============================================================================
# CONVERSION UTILITIES
#==============================================================================

    def object_to_json(self, obj):
        """
        Convert a given object to a json string using the simplifier

        Parameters
        ----------
        obj : the object to be converted

        Returns
        -------
        str
            the JSON string
        """
        json_string = self.simplifier.to_json_object(obj, obj.base_cls_name)

        return json_string

    def list_to_numpy(self, data, value_type, allow_empty = True):
        """
        Return a numpy list from a python list in a given format

        Parameters
        ----------
        data : list
            the list to be converted
        value_type : str
            the type of the input list elements. If this is an object type it
            will be saved and the returned index is stored in an numpy
            integer array
        allow_empty : bool
            if set to `True` None will be stored as the integer -1

        Returns
        -------
        numpy.ndarray
            the converted numpy array
        """
        if value_type == 'int':
            values = np.array(data).astype(np.float32)
        elif value_type == 'float':
            values = np.array(data).astype(np.float32)
        elif value_type == 'bool':
            values = np.array(data).astype(np.uint8)
        elif value_type == 'index':
            values = np.array(data).astype(np.int32)
        elif value_type == 'length':
            values = np.array(data).astype(np.int32)
        else:
            # an object
            values = [-1 if value is None and allow_empty is True
                      else value.idx[self] for value in data]
            values = np.array(values).astype(np.int32)

        return values.copy()

    def list_from_numpy(self, values, value_type, allow_empty = True):
        """
        Return a python list from a numpy array in a given format

        Parameters
        ----------
        values : numpy.ndarray
            the numpy array to be converted
        value_type : str
            the type of the output list elements. If this is a object type it
            will be loaded using the numpy array content as the index
        allow_empty : bool
            if set to `True` then loaded objects will only be loaded if the
            index is not negative. Otherwise the load function will always
            be called

        Returns
        -------
        list
            the converted list
        """
        if value_type == 'int':
            data = values.tolist()
        elif value_type == 'float':
            data = values.tolist()
        elif value_type == 'bool':
            data = values.tolist()
        elif value_type == 'index':
            data = values.tolist()
        elif value_type == 'length':
            data = values.tolist()
        else:
            # an object
            key_store = getattr(self.storage, value_type)
            data = [key_store.load(obj_idx) if allow_empty is False
                    or obj_idx >= 0 else None for obj_idx in values.tolist()]

        return data

#==============================================================================
# SETTER / GETTER UTILITY FUNCTIONS
#==============================================================================

    # TODO: This might go tho storage.py
    def load_object(self, name, idx, store):
        """
        Load an object from the storage

        Parameters
        ----------
        name : str
            name of the variable to be used
        index : int
            index in the storage
        cls : cls
            type of the object to be loaded. Determines the store to be used

        Returns
        -------
        object
            the loaded object
        """
        index = self.load_variable(name + '_idx', idx)
        if index < 0:
            return None

        obj = store.load(index)
        return obj


#==============================================================================
# COLLECTIVE VARIABLE UTILITY FUNCTIONS
#==============================================================================

    @property
    def op_idx(self):
        """
        Returns a function that returns for an object of this storage the idx.
        This can be used to construct order parameters the return the index
        in this storage. Useful for visualization

        Returns
        -------
        function
            the function that reports the index in this store
        """
        def idx(obj):
            return obj.idx[self]

        return idx

#=============================================================================
# LOAD/SAVE DECORATORS FOR PARTIAL LOADING OF ATTRIBUTES
#=============================================================================

def loadpartial(func, constructor=None):
    """
    Decorator for load functions that add the basic handling for partial loading
    """

    def inner(self, idx, *args, **kwargs):
        if constructor is None:
            new_func = getattr(self, 'load_empty')
        else:
            new_func = getattr(self, constructor)

        return_obj = new_func(idx, *args, **kwargs)
        # this tells the obj where it was loaded from
        return_obj._origin = self
        return return_obj

    return inner


#=============================================================================
# LOAD/SAVE DECORATORS FOR CACHE HANDLING
#=============================================================================

def loadcache(func):
    """
    Decorator for load functions that add the basic cache handling
    """
    def inner(self, idx, *args, **kwargs):
        if type(idx) is not str and idx < 0:
            return None

        if not hasattr(self, 'cache'):
            return func(idx, *args, **kwargs)

        n_idx = idx

        if type(idx) is str:
            # we want to load by name and it was not in cache.
            if self.has_name:
                # since it is not found in the cache before. Refresh the cache
                self.update_name_cache()

                # and give it another shot
                if idx in self.name_idx:
                    if len(self.name_idx[idx]) > 1:
                        logger.debug('Found name "%s" multiple (%d) times in storage! Loading first!' % (idx, len(self.cache[idx])))

                    n_idx = self.name_idx[idx][0]
                else:
                    raise ValueError('str "' + idx + '" not found in storage')
        elif type(idx) is int:
            pass
        else:
            raise ValueError('str "' + idx + '" as indices are only allowed in named storage')

        # if it is in the cache, return it
        if n_idx in self.cache:
            logger.debug('Found IDX #' + str(idx) + ' in cache. Not loading!')
            return self.cache[n_idx]

        # ATTENTION HERE!
        # Note that the wrapped function no self as first parameter. This is because we are wrapping a bound
        # method in an instance and this one is still bound - luckily - to the same 'self'. In a class decorator when wrapping
        # the class method directly it is not bound yet and so we need to include the self! Took me some time to
        # understand and figure that out

        obj = func(n_idx, *args, **kwargs)
        if obj is not None:
            # update cache there might have been a change due to naming
            self.cache[obj.idx[self]] = obj

            # finally store the name of a named object in cache
            if self.has_name and obj._name != '':
                self._update_name_in_cache(obj._name, n_idx)

        return obj
    return inner

# the default decorator for save functions to enable caching
def savecache(func):
    """
    Decorator for save functions that add the basic cache handling
    """
    def inner(self, obj, idx = None, *args, **kwargs):
        # call the normal storage
        func(obj, idx, *args, **kwargs)
        idx = obj.idx[self]

        # store the name in the cache
        if hasattr(self, 'cache'):
            self.cache[idx] = obj
            if self.has_name and obj._name != '':
                # and also the name, if it has one so we can load by
                # name afterwards from cache
                self._update_name_in_cache(obj._name, idx)

        return idx

    return inner

#=============================================================================
# LOAD/SAVE DECORATORS FOR .idx HANDLING
#=============================================================================

def loadidx(func):
    """
    Decorator for load functions that add the basic indexing handling
    """
    def inner(self, idx, *args, **kwargs):
        if type(idx) is not str and int(idx) < 0:
            return None

        n_idx = idx

        if type(idx) is str:
            # we want to load by name and it was not in cache
            if self.has_name:
                raise ValueError('Load by name without caching is not supported')
#                n_idx = self.load_by_name(idx)
            else:
                # load by name only in named storages
                raise ValueError('Load by name (str) is only supported in named storages')
                pass

        # turn into python int if it was a numpy int (in some rare cases!)
        n_idx = int(n_idx)

        # ATTENTION HERE!
        # Note that the wrapped function ho self as first parameter. This is because we are wrapping a bound
        # method in an instance and this one is still bound - luckily - to the same 'self'. In a class decorator when wrapping
        # the class method directly it is not bound yet and so we need to include the self! Took me some time to
        # understand and figure that out
        logger.debug('Calling load object of type ' + self.content_class.__name__ + ' and IDX #' + str(idx))
        if n_idx >= len(self):
            logger.warning('Trying to load from IDX #' + str(n_idx) + ' > number of object ' + str(len(self)))
            return None
        elif n_idx < 0:
            logger.warning('Trying to load negative IDX #' + str(n_idx) + ' < 0')
            return None
        else:
            obj = func(n_idx, *args, **kwargs)

        if not hasattr(obj, 'idx'):
            print type(obj), obj.__dict__
#            obj.idx = dict()

        obj.idx[self] = n_idx

        if self.has_uid:
            if not hasattr(obj, '_uid'):
                # get the name of the object
                setattr(obj, '_uid', self.get_uid(idx))

        if self.has_name and hasattr(obj, '_name'):
            setattr(obj, '_name',
                    self.storage.variables[self.prefix + '_name'][idx])
            # make sure that you cannot change the name of loaded objects
            obj.fix_name()

        return obj

    return inner

def saveidx(func):
    """
    Decorator for save functions that add the basic indexing handling
    """
    def inner(self, obj, idx = None, *args, **kwargs):
        storage = self.storage
        if idx is None:
            if self in obj.idx:
                # has been saved so quit and do nothing
                return obj.idx[self]
            else:
                idx = self.free()
        else:
            if type(idx) is str:
                # Not yet supported
                raise ValueError('Saving by name not yet supported')
            else:
                idx = int(idx)

        obj.idx[self] = idx

        # make sure in nested saving that an IDX is not used twice!
        self.reserve_idx(idx)
        logger.debug('Saving ' + str(type(obj)) + ' using IDX #' + str(idx))
        func(obj, idx, *args, **kwargs)

        if self.has_uid and hasattr(obj, '_uid') and obj._uid != '':
            self.storage.variables[self.identifier][idx] = obj._uid

        if self.has_name and hasattr(obj, '_name'):
            #logger.debug('Object ' + str(type(obj)) + ' with IDX #' + str(idx))
            #logger.debug(repr(obj))
            #logger.debug("Cleaning up name; currently: " + str(obj._name))
            if obj._name is None:
                # this should not happen!
                logger.debug("Nameable object has not been initialized correctly. Has None in _name")
                raise AttributeError('_name needs to be a string for nameable objects.')

            obj.fix_name()

            self.storage.variables[self.prefix + '_name'][idx] = obj._name

        return idx

    return inner

# CREATE EASY UPDATE WRAPPER

def func_update_variable(attribute, variable):
    """
    Create a delayed loading function for stores

    Parameters
    ----------
    attribute : string
        name of the attribute of the object to be updated. E.g. for sample.mover this is 'mover'
    db : string
        the storage prefix where the object are stored in the file. E.g. for samples this is 'sample'
    variable : string
        the name of the variable in the storage. this is often the same as the attribute
    store : string
        the name of the store. E.g. 'trajectories'

    Returns
    -------
    function
        the function that is used for updating
    """
    def updater(obj):
        store = obj._origin
        idx = obj.idx[store]

#        print 'updater called', obj, obj.__dict__.keys(), attribute, variable

        value = store.vars[variable][idx]
        setattr(obj, attribute, value)

    return updater

def create_load_function(cls, arguments):
    def loader(self, idx):
        params = {arg : self.vars[param][idx] for arg, param in arguments.iteritems()}

        return cls(**params)

    return loader
