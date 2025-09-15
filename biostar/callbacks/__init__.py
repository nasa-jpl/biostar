from dash import Dash

from .configure import attach_callbacks as callbacks_configure
from .delete import attach_callbacks as callbacks_delete
from .diffs import attach_callbacks as callbacks_diffs
from .display import attach_callbacks as callbacks_display
from .import_export import attach_callbacks as callbacks_import_export
from .record import attach_callbacks as callbacks_record
from .results import attach_callbacks as callbacks_results


def attach_callbacks(app: Dash) -> None:
    """"""

    callbacks_diffs(app)
    callbacks_record(app)
    callbacks_delete(app)
    callbacks_configure(app)
    callbacks_display(app)
    callbacks_results(app)
    callbacks_import_export(app)
