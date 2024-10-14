import inspect
from typing import Literal

CALLER_NAME_FORMAT = Literal["module", "class", "method"]


def get_caller_name(return_format: CALLER_NAME_FORMAT = "method", skip: int = 2):
    """Get a name of a caller in the format module.class.method

    `skip` specifies how many levels of stack to skip while getting caller
    name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

    An empty string is returned if skipped levels exceed stack height
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return ""
    parentframe = stack[start][0]

    name = []
    module = inspect.getmodule(parentframe)

    if return_format == "module" and module:
        name.append(module.__name__)

    if (return_format in ("module", "class")) and "self" in parentframe.f_locals:
        name.append(parentframe.f_locals["self"].__class__.__name__)

    codename = parentframe.f_code.co_name
    if codename != "<module>":  # top level usually
        name.append(codename)  # function or a method

    del parentframe, stack

    return ".".join(name)
