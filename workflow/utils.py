import shutil
import os

def mkdir(path, reset=False):
    """Checks if directory exists and if not, create one.

    Parameters
    ----------
    reset: erase the content of the directory if exists

    Returns
    -------
    the path
    """

    if reset and os.path.exists(path):
        shutil.rmtree(path)
    try:
        os.makedirs(path)
    except FileExistsError:
        pass
    return path
