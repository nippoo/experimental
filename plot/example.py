import numpy as np
from vispy import app, keys
from vispy.visuals import TextVisual
from loader import DataLoader, PanZoomCanvas, SignalsVisual

if __name__ == '__main__':

    filename = '/data/spikesorting/nick128_sorted/20141009_all_AdjGraph.raw.kwd'
    loader = DataLoader(filename, page_duration=1, nchannels=128)

    c = PanZoomCanvas(position=(400, 300), size=(800,600))
    c.signals = SignalsVisual(loader.data)
    # c.text = TextVisual(text='hey', color='white', pos=(100,100), font_size=48)

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
