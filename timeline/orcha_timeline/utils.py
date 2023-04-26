import colorsys
import matplotlib.colors as mcolors


def adjust_lightness(color, scale_l=1.0):
    if color is None:
        return None

    h, l, s = colorsys.rgb_to_hls(*mcolors.to_rgb(color))
    return colorsys.hls_to_rgb(h, min(1, l * scale_l), s=s)
