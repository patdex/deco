import collections
import inspect
import time
import re


# module config:
disable_tracing = False
indent = True

# indentation for log output
_log_indent = dict()


def indent_str(cnt, end=False):
    """
    indent string
    :param cnt: indentation count
    :param end: close actual indentation?
    :return: 
    """

    if not indent:
        return ''

    return '| ' * cnt + ('/ ' if not end else '\\ ')


class _MyOrderedDict(collections.OrderedDict):
    """
    format representation string vor log output
    """
    def __repr__(self):
        ret = str()
        for key, val in self.items():
            ret += '{0}={2}({1}), '.format(key, val, val.__class__.__name__)
        return ret[:-2]


class _MyList(list):
    """
    format representation string vor log output
    """
    def __repr__(self):
        ret = str()
        for val in self:
            ret += '{0}({1}), '.format(val, val.__class__.__name__)
        return ret[:-2]


def _get_wrapped_method(func):
    """
    get inner method if multiple decorators are used
    :param func: 
    :return: 
    """
    while hasattr(func, '__wrapped__'):
        func = getattr(func, '__wrapped__')
    return func


def _wrap(wrapper, func):
    """
    save wrapped function if multiple decorators are used
    :param func: 
    :return: 
    """
    setattr(wrapper, '__wrapped__', func)


def argument_types(func):
    """
    :param func: 
    :return: dictionary with argument name and type 
    """
    signature = inspect.signature(func)
    sig = re.match(r"\(([^)]+)\)", str(signature)).group(1)
    param_list = str(sig).split(', ')
    types = dict()
    for param in param_list:
        try:
            elements = param.split(':')
            types[elements[0]] = elements[1].split('=')[0]
        except IndexError:
            pass
    return types


def collect_all_arguments_to_dict(func, args, kwargs):
    """
    :param func: 
    :param args: 
    :param kwargs: 
    :return: dictionary with all method arguments and their values (like kwargs)
    """
    arg_names = [arg_name for arg_name in inspect.signature(func).parameters]
    all_as_kwargs = _MyOrderedDict()

    # collect args
    for arg_name, arg_val in zip(arg_names, args):
        all_as_kwargs[arg_name] = arg_val

    # collect kwargs
    for arg_name in arg_names:
        if arg_name in kwargs:
            all_as_kwargs[arg_name] = kwargs[arg_name]

    # collect default arguments:
    for arg_name, arg_val in inspect.signature(func).parameters.items():
        if arg_name in arg_names and arg_name not in all_as_kwargs:
            all_as_kwargs[arg_name] = arg_val.default

    return all_as_kwargs


class Trace:
    """
    Decorator Class
    """
    def __init__(self, log_method, disable=False):
        """
        :param log_method: logging method
        :param disable: disable logging
        """
        self.log_method = log_method
        self.disabled = disable

    def __call__(self, func):
        """
        :param func: decorated method
        :return: 
        """
        def wrapper(*args, **kwargs):

            if self.disabled or disable_tracing:
                return func

            inner_func = _get_wrapped_method(func)

            ind = self._increment_indent()  # indent log message
            all_as_kwargs = collect_all_arguments_to_dict(inner_func, args, kwargs)  # all arguments to OrderedDict
            self.log_method(indent_str(ind) + self._call_message(inner_func, all_as_kwargs))
            start_time = time.time()

            ret = func(*args, **kwargs)  # run decorated method

            exec_time = time.time() - start_time
            self.log_method(indent_str(ind, True) + self._return_message(inner_func, ret, exec_time))
            self._decrement_indent()  # redo indent log message
            return ret

        _wrap(wrapper, func)
        return wrapper

    @staticmethod
    def _call_message(func, all_as_kwargs):
        """
        format call log message
        :param func: 
        :param all_as_kwargs: 
        :return: 
        """
        message = '{0}({1})'.format(func.__name__, all_as_kwargs)
        return message

    @staticmethod
    def _return_message(func, ret, exec_time):
        """
        format return log message
        :param func: 
        :param ret: 
        :return: 
        """
        ret_arg_str = str(_MyList(ret)) if isinstance(ret, tuple) else '{1}({0})'.format(ret, ret.__class__.__name__)
        message = '{1} in {2:.3f}ms'.format(func.__name__, ret_arg_str, exec_time * 1000)

        return message

    def _increment_indent(self):

        if not indent:
            return ''

        if self.log_method not in _log_indent:
            _log_indent[self.log_method] = 0
        else:
            _log_indent[self.log_method] += 1
        return _log_indent[self.log_method]

    def _decrement_indent(self):

        if not indent:
            return ''

        _log_indent[self.log_method] -= 1


def cast_std_arguments(func):
    """
    cast arguments with standard and defined type
    :param func: 
    :return: 
    """
    def wrapper(*args, **kwargs):

        inner_func = _get_wrapped_method(func)

        all_as_kwargs_casted = collections.OrderedDict()
        all_as_kwargs = collect_all_arguments_to_dict(inner_func, args, kwargs)  # all arguments to OrderedDict
        arg_types = argument_types(inner_func)

        for arg_name, arg_value in all_as_kwargs.items():
            arg_type = arg_types.get(arg_name, None)
            if arg_type:  # if type defined:
                try:      # try to cast
                    arg_value = eval('{0}(arg_value)'.format(arg_type))
                except NameError:  # unknown namespace
                    pass
            all_as_kwargs_casted[arg_name] = arg_value

        # run decorated method with casted arguments
        return func(**all_as_kwargs_casted)

    _wrap(wrapper, func)
    return wrapper
