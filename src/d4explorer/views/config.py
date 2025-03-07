import holoviews as hv
from holoviews.plotting.util import process_cmap

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
