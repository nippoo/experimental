from vispy import gloo
from vispy import app
from vispy.visuals import Visual
import numpy as np
import os.path as op
import math

class SignalsVisual(Visual):
    VERTEX_SHADER = """
    #version 120
    attribute float a_position;

    attribute vec2 a_index;
    varying vec2 v_index;

    uniform vec2 u_scale;
    uniform vec2 u_pan;
    uniform float u_size;
    uniform float u_n;

    attribute vec3 a_color;
    varying vec4 v_color;

    void main() {
        float nrows = u_size;

        float x = -1 + 2*a_index.y / (u_n-1);
        vec2 position = vec2(x, a_position);

        float a = 1./nrows;
        float b = -1 + 2*(a_index.x+.5) / nrows;
        vec2 position_tr = vec2(position.x, a*5*position.y+b);

        gl_Position = vec4(u_scale * (position_tr + u_pan), 0.0, 1.0);

        v_color = vec4(a_color, 1.);
        v_index = a_index;
    }
    """

    FRAGMENT_SHADER = """
    #version 120

    varying vec4 v_color;
    varying vec2 v_index;

    void main() {
        gl_FragColor = v_color;

        // Discard vertices between two signals.
        if ((fract(v_index.x) > 0.))
            discard;
    }
    """

    def __init__(self, signals):
        self.program = gloo.Program(self.VERTEX_SHADER, self.FRAGMENT_SHADER)

        m, n = signals.shape
        y = signals
        color = np.repeat(np.random.uniform(size=(m, 3), low=.5, high=.9),
                              n, axis=0).astype(np.float32)
        index = np.c_[np.repeat(np.arange(m), n),
                      np.tile(np.arange(n), m)].astype(np.float32)

        self.program['a_position'] = y.reshape(-1, 1)
        self.program['a_color'] = color
        self.program['a_index'] = index
        self.program['u_scale'] = (1., 1.)
        self.program['u_pan'] = (0., 0.)
        self.program['u_size'] = m
        self.program['u_n'] = n

    def draw(self):
        self.program.draw('line_strip')


if __name__ == '__main__':
    # m = 16
    # n = 1000

    filename = '/data/spikesorting/Dropbox (Neuropixels)/Achilles1025/Achilles151_10252013_postsleep_reo.dat'
    filesize = op.getsize(filename)
    nchannels = 151
    nsamples = filesize//(nchannels*2)

    data = np.memmap(filename, dtype='int16', mode='r', shape=(nsamples, nchannels))
    data = data[:5*20000,:].T.astype(np.float32)

    # y = np.random.randn(m, n).astype(np.float32)
    data /= np.abs(data).max()
    v = SignalsVisual(data)

    c = app.Canvas(keys='interactive')

    @c.connect
    def on_initialize(event):
        gloo.set_state(clear_color='black', blend=True,
                       blend_func=('src_alpha', 'one_minus_src_alpha'))

    @c.connect
    def on_resize(event):
        c.width, c.height = event.size
        gloo.set_viewport(0, 0, c.width, c.height)

    def _normalize(x_y):
        x, y = x_y
        w, h = float(c.width), float(c.height)
        return x/(w/2.)-1., y/(h/2.)-1.

    @c.connect
    def on_mouse_move(event):
        if event.is_dragging:
            x0, y0 = _normalize(event.press_event.pos)
            x1, y1 = _normalize(event.last_event.pos)
            x, y = _normalize(event.pos)
            dx, dy = x - x1, -(y - y1)
            button = event.press_event.button

            pan_x, pan_y = v.program['u_pan']
            scale_x, scale_y = v.program['u_scale']

            if button == 1:
                v.program['u_pan'] = (pan_x+dx/scale_x, pan_y+dy/scale_y)
            elif button == 2:
                scale_x_new, scale_y_new = (scale_x * math.exp(2.5*dx),
                                            scale_y * math.exp(2.5*dy))
                v.program['u_scale'] = (scale_x_new, scale_y_new)
                v.program['u_pan'] = (pan_x -
                                         x0 * (1./scale_x - 1./scale_x_new),
                                         pan_y +
                                         y0 * (1./scale_y - 1./scale_y_new))
            c.update()

    @c.connect
    def on_mouse_wheel(event):
        dx = np.sign(event.delta[1])*.05
        x0, y0 = _normalize(event.pos)
        pan_x, pan_y = v.program['u_pan']
        scale_x, scale_y = v.program['u_scale']
        scale_x_new, scale_y_new = (scale_x * math.exp(2.5*dx),
                                    scale_y * math.exp(2.5*dx))
        v.program['u_scale'] = (scale_x_new, scale_y_new)
        v.program['u_pan'] = (pan_x -
                                 x0 * (1./scale_x - 1./scale_x_new),
                                 pan_y +
                                 y0 * (1./scale_y - 1./scale_y_new))
        c.update()

    @c.connect
    def on_draw(event):
        gloo.clear()
        v.draw()

    c.show()
    app.run()