import math
import numpy as np
import h5py

from vispy import app, keys
from signals import SignalsVisual
from panzoomcanvas import PanZoomCanvas


def channel_scale(data):
    m, M = data.min(), data.max()
    scale = 1. / max(math.fabs(m), math.fabs(M))
    return scale


# @profile
def load_data(filename, sample_start=0, sample_stop=None, scale=None):
    with h5py.File(filename) as f:
        data = f['/recordings/0/data']
        if sample_stop is None:
            sample_stop = f['/recordings/0'].attrs['sample_rate']

        # Data selection.
        # WARNING: beware the transposition (necessary to load contiguous
        # data on the GPU, but can be worked around later with an index buffer)
        data = data[sample_start:sample_stop,:]
        data = data.astype(np.float32)
        data = data.T.copy()

        # Data normalization.
        mean = data.mean(axis=1)[:, None]
        data -= mean
        data *= scale

    return data


def get_data_info(filename):
    with h5py.File(filename) as f:
        data = f['/recordings/0/data']
        return data.shape, f['/recordings/0'].attrs['sample_rate']


class Pager(object):
    def __init__(self, nsamples_total=None, nsamples_page=None):
        self.nsamples_total = int(nsamples_total)
        self.nsamples_page = int(nsamples_page)
        self._index = 0
        self._page_max = self.to_page(self.nsamples_total - 1)

    def to_page(self, sample):
        return sample // self.nsamples_page

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, value):
        self._index = np.clip(value, 0, self._page_max - 1)

    @property
    def page_max(self):
        return self._page_max

    # @property
    def bounds(self):
        return (self.nsamples_page * self._index,
                self.nsamples_page * (self._index + 1))


class DataLoader(object):
    def __init__(self, filename, page_duration=1.):
        self.filename = filename
        (self.nsamples_total, self.nchannels), self.sample_rate = get_data_info(filename)
        self.pager = Pager(nsamples_total=self.nsamples_total,
                           nsamples_page=page_duration * self.sample_rate)
        self._scale = None
        self._load()

    def _load(self):
        start, stop = self.pager.bounds()
        self.data = load_data(self.filename, start, stop,
                              scale=self._scale or 1.)
        if self._scale is None:
            self._scale = channel_scale(self.data)
            self.data *= self._scale
        print("Page", self.pager.index)
        return self.data

    def next(self):
        self.pager.index += 1
        return self._load()

    def previous(self):
        self.pager.index -= 1
        return self._load()

    def from_time(self, time):
        return self.from_sample(int(time * self.sample_rate))

    def from_sample(self, sample):
        self.index = self.to_page(sample)
        return self._load()

    def first(self):
        self.pager.index = 0
        return self._load()

    def last(self):
        self.pager.index = self.pager.page_max - 1
        return self._load()


if __name__ == '__main__':

    filename = '/data/spikesorting/nick128_sorted/20141009_all_AdjGraph.raw.kwd'
    loader = DataLoader(filename, page_duration=1)

    c = PanZoomCanvas()
    c.signals = SignalsVisual(loader.data)


    @c.connect
    def on_mouse_wheel(event):
        if event.modifiers == (keys.CONTROL,):
            sign = np.sign(event.delta[1])
            c.signals.signal_scale = np.clip(c.signals.signal_scale*1.2**sign,
                                             1e-2, 1e2)

    @c.connect
    def on_key_press(event):
        if event.key == 'Left':
            c.signals.data = loader.previous()
            c.update()
        elif event.key == 'right':
            c.signals.data = loader.next()
            c.update()
        elif event.key == 'Home':
            c.signals.data = loader.first()
            c.update()
        elif event.key == 'End':
            c.signals.data = loader.last()
            c.update()

    app.run()

