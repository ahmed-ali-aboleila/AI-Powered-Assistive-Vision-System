from src.voice.logic_controller import *  # noqa: F401,F403
from src.voice.logic_controller import __dict__ as _module_dict

globals().update({k: v for k, v in _module_dict.items() if not k.startswith('__')})
