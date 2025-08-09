import os
import glob
import logging
import threading

DEFAULT_MODEL_PATH = "/content/drive/MyDrive/models/RVC/G_8200.pth"
DISCOVERY_PATTERN = "/content/drive/MyDrive/models/RVC/*.pth"
ENV_VAR = "RVC_MODEL"


def discover_models(pattern: str = DISCOVERY_PATTERN):
    """Return a sorted list of available model files."""
    return sorted(glob.glob(pattern))


def _select_model(candidates):
    """Interactively choose a model from the list.

    Uses a notebook dropdown when ``ipywidgets`` is available, otherwise
    falls back to simple CLI input.
    """
    try:
        from IPython.display import display
        import ipywidgets as widgets

        event = threading.Event()
        dropdown = widgets.Dropdown(
            options=[(os.path.basename(p), p) for p in candidates],
            description="Model:",
        )
        button = widgets.Button(description="Select")

        def _on_click(_):
            event.set()

        button.on_click(_on_click)
        display(dropdown, button)
        event.wait()
        return dropdown.value
    except Exception:
        print("Available models:")
        for idx, model in enumerate(candidates, 1):
            print(f"{idx}: {model}")
        choice = input("Select model number: ")
        try:
            idx = int(choice) - 1
            return candidates[idx]
        except (ValueError, IndexError):
            raise FileNotFoundError(f"Invalid selection '{choice}'")


def get_model_path(cli_path: str = None, *, env_var: str = ENV_VAR,
                   default: str = DEFAULT_MODEL_PATH,
                   pattern: str = DISCOVERY_PATTERN,
                   use_ui: bool = False):
    """Determine which model path to use.

    Priority: CLI argument > environment variable > default path. If the
    resulting path does not exist, fall back to discovered models. When
    ``use_ui`` is True and multiple models are available, the user is asked to
    choose one interactively.
    """
    candidates = discover_models(pattern)
    path = cli_path or os.getenv(env_var) or default
    if not os.path.isfile(path):
        if not candidates:
            raise FileNotFoundError(
                f"Model path '{path}' not found and no models available in '{pattern}'. "
                "Please upload an RVC model to /content/drive/MyDrive/models/RVC/",
            )
        if use_ui and len(candidates) > 1:
            path = _select_model(candidates)
        else:
            path = candidates[0]
    logging.info("Using model: %s", path)
    return path
