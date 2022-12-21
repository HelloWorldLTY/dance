import numpy as np

from dance.transforms.base import BaseTransform
from dance.typing import Sequence
from dance.utils.matrix import pairwise_distance


class SpaGCNGraph(BaseTransform):

    def __init__(self, alpha, beta, *, channels: Sequence[str] = ("spatial", "spatial_pixel", "image"),
                 channel_types: Sequence[str] = ("obsm", "obsm", "uns"), **kwargs):
        """Initialize SpaGCNGraph.

        Parameters
        ----------
        alpha
            Controls the color scale.
        beta
            Controls the range of the neighborhood when calculating grey values for one spot.

        """
        super().__init__(**kwargs)

        self.alpha = alpha
        self.beta = beta
        self.channels = channels
        self.channel_types = channel_types

    def __call__(self, data):
        xy = data.get_feature(return_type="numpy", channel=self.channels[0], channel_type=self.channel_types[0])
        xy_pixel = data.get_feature(return_type="numpy", channel=self.channels[1], channel_type=self.channel_types[1])
        img = data.get_feature(return_type="numpy", channel=self.channels[2], channel_type=self.channel_types[2])
        self.logger.info("Start calculating the adjacency matrix using the histology image")

        g = np.zeros((xy.shape[0], 3))
        beta_half = round(self.beta / 2)
        x_lim, y_lim = img.shape[:2]
        for i, (x_pixel, y_pixel) in enumerate(xy_pixel):
            top = max(0, x_pixel - beta_half)
            left = max(0, y_pixel - beta_half)
            bottom = min(x_lim, x_pixel + beta_half + 1)
            right = min(y_lim, y_pixel + beta_half + 1)
            local_view = img[top:bottom, left:right]
            g[i] = np.mean(local_view, axis=(0, 1))
        g_var = g.var(0)
        self.logger.info(f"Variances of c0, c1, c2 = {g_var}")

        z = (g * g_var).sum(1, keepdims=True) / g_var.sum()
        z = (z - z.mean()) / z.std()
        z *= xy.std(0).max() * self.alpha

        xyz = np.hstack((xy, z)).astype(np.float32)
        self.logger.info(f"Varirances of x, y, z = {xyz.var(0)}")
        data.data.obsp[self.out] = pairwise_distance(xyz, dist_func_id=0)

        return data


class SpaGCNGraph2D(BaseTransform):

    def __init__(self, *, channel: str = "spatial_pixel", **kwargs):
        super().__init__(**kwargs)

        self.channel = channel

    def __call__(self, data):
        x = data.get_feature(channel=self.channel, channel_type="obsm", return_type="numpy")
        data.data.obsp[self.out] = pairwise_distance(x.astype(np.float32), dist_func_id=0)
        return data