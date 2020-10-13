import sys

from .image import *

_custom_multimodal_transforms = sys.modules[__name__]


def instantiate_multimodal_transform(transform_option, attr="transform"):
    """ Creates a transform from an OmegaConf dict such as:
    transform: GridSampling3D
        params:
            size: 0.01
    """


    tr_name = getattr(transform_option, attr, None)
    try:
        tr_params = transform_option.params
    except KeyError:
        tr_params = None


    cls = getattr(_custom_multimodal_transforms, tr_name, None)
    if not cls:
        raise ValueError(f"Multimodal transform {tr_name} is nowhere to be found")


    if tr_params:
        return cls(**tr_params)

    return cls()