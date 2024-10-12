import inspect


def get_caller_name() -> str:
    caller_name = ""
    frames = inspect.stack()

    for f in frames:
        if f.function == "<module>":
            return caller_name
        caller_name = f.function
