"""Config file.

This file stores configurations for the entire application such as figure
dimensions and color schemes.
"""

import holoviews as hv
from holoviews.plotting.util import process_cmap

# Global plot settings
PLOT_WIDTH = 1000
PLOT_HEIGHT = 600
THRESHOLD = 1000  # max number of points to overlay on a plot
PLOT_COLOURS = ["#15E3AC", "#0FA57E", "#0D5160"]

# VCard settings
SIDEBAR_BACKGROUND = "#5CB85D"
VCARD_STYLE = {
    "background": "WhiteSmoke",
}

# Global color map
CMAP = "viridis"
CMAP_GLASBEY = {
    cm.name: cm
    for cm in hv.plotting.util.list_cmaps(
        records=True, category="Categorical", reverse=False
    )
    if cm.name.startswith("glasbey")
}
colormap = "glasbey_hv"
COLORS = process_cmap(
    CMAP_GLASBEY[colormap].name, provider=CMAP_GLASBEY[colormap].provider
)
