# SPDX-License-Identifier: GPL-3.0-or-later
"""Neo Dark reusable views; every network/disk task runs off the GUI thread."""
import queue
import threading
from pathlib import Path
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from enigma import eTimer, getDesktop


class ChannelRows:
    """Build labels only for the visible page, including very large IPTV groups."""
    def __init__(self, services):
        self.services = services

    def __len__(self):
        return len(self.services)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self.row(s) for s in self.services[index]]
        return self.row(self.services[index])

    @staticmethod
    def row(service):
        return ('%s  ·  %s' % (service['name'] or 'Sans nom', service['kind']), service)


class Worker:
    def setup_worker(self):
        self.busy = False
        self._events = queue.Queue()
        self._timer = eTimer()
        self._timer.callback.append(self._poll)
        self.onClose.append(self._timer.stop)

    def work(self, task, done):
        if self.busy:
            return
        self.busy = True
        self['status'].setText('Opération en cours…')
        def run():
            try:
                result = (done, task(), None)
            except Exception as exc:
                result = (done, None, exc)
            self._events.put(result)
        threading.Thread(target=run, name='PiconManagerNG-worker', daemon=True).start()
        self._timer.start(100, False)

    def _poll(self):
        try:
            done, value, error = self._events.get_nowait()
        except queue.Empty:
            return
        if done is None:
            self['status'].setText(value)
            return
        self._timer.stop()
        self.busy = False
        self['status'].setText('Prêt')
        if error:
            # No stream URL or traceback is exposed in the product UI.
            message = str(error) if isinstance(error, (ValueError, RuntimeError)) else 'Opération impossible. Vérifiez la connexion et l’espace disponible.'
            self.session.open(MessageBox, message, MessageBox.TYPE_ERROR)
        else:
            done(value)

    def progress(self, text):
        # Keep the queue bounded even while large bouquets scan faster than paints.
        if self._events.qsize() < 4:
            self._events.put((None, text, None))

    def leave(self):
        if self.busy:
            self['status'].setText('Veuillez attendre la fin de l’opération…')
        else:
            self.close()


def browser_skin(width):
    scale = 1.5 if width >= 1800 else 1
    def n(value):
        return int(value * scale)
    def rect(x, y, w, h):
        return 'position="%d,%d" size="%d,%d"' % tuple(n(v) for v in (x, y, w, h))
    def label(name, x, y, w, h, font=23, extra=''):
        return '<widget name="%s" %s font="Regular;%d" foregroundColor="#F1F5FE" backgroundColor="#111B2C" %s />' % (name, rect(x,y,w,h), n(font), extra)
    return ('<screen name="PiconManagerNGBrowser" position="center,center" size="%d,%d" flags="wfNoBorder" backgroundColor="#080D18">' % (n(1280), n(720)) +
            label('title', 40, 30, 1195, 55, 35) +
            label('rows', 40, 110, 700, 470, 22, 'itemHeight="%d" foregroundColorSelected="#FFFFFF" backgroundColorSelected="#244461" enableWrapAround="1"' % n(39)) +
            label('detail', 775, 110, 460, 75, 19) +
            label('before_label', 790, 198, 400, 30, 19) +
            '<widget name="before" %s alphatest="blend" />' % rect(865, 234, 250, 150) +
            label('after_label', 790, 405, 400, 30, 19) +
            '<widget name="after" %s alphatest="blend" />' % rect(865, 441, 250, 150) +
            label('status', 40, 600, 1195, 35, 20) +
            label('footer', 40, 652, 1195, 35, 20) + '</screen>')


class Browser(Screen, Worker):
    PAGE = 250

    def __init__(self, session, title, rows, detail=None, green=None, yellow=None,
                 blue=None, ok=None, footer='ROUGE Retour', selectable=False):
        self.skin = browser_skin(getDesktop(0).size().width())
        Screen.__init__(self, session)
        # Screen is a dict and calls items() when destroying widgets on exit.
        self.entries = rows
        self.page = 0
        self.selected = set()
        self.selectable = selectable
        self.detail_callback = detail or (lambda row: (row[0], None, None))
        self.callbacks = {'green': green, 'yellow': yellow, 'blue': blue, 'ok': ok}
        self['title'] = Label(title)
        self['rows'] = MenuList([])
        self['detail'] = Label('')
        self['before_label'] = Label('Actuel')
        self['after_label'] = Label('Proposé')
        self['before'] = Pixmap()
        self['after'] = Pixmap()
        self['status'] = Label('')
        self['footer'] = Label(footer)
        self['keys'] = ActionMap(['OkCancelActions', 'ColorActions', 'DirectionActions'],
            {'cancel': self.leave, 'red': self.leave, 'ok': lambda: self.action('ok'),
             'green': lambda: self.action('green'), 'yellow': lambda: self.action('yellow'),
             'blue': lambda: self.action('blue'), 'left': lambda: self.turn_page(-1),
             'right': lambda: self.turn_page(1), 'up': self['rows'].up, 'down': self['rows'].down}, -1)
        self['rows'].onSelectionChanged.append(self.focus)
        self.setup_worker()
        self.onLayoutFinish.append(self.refresh)

    def current(self):
        value = self['rows'].getCurrent()
        return value[1] if value else None

    def refresh(self):
        start = self.page * self.PAGE
        visible = self.entries[start:start+self.PAGE]
        self['rows'].setList([(('☑ ' if start+i in self.selected else '☐ ') if self.selectable else '') + row[0]
                              for i, row in enumerate(visible)])
        # MenuList keeps plain labels to avoid copying all 100,000 services.
        self['status'].setText('%d éléments • page %d/%d • %d sélectionnés' %
            (len(self.entries), self.page+1, max(1, (len(self.entries)+self.PAGE-1)//self.PAGE), len(self.selected)))
        self.focus()

    def index(self):
        if not self.entries:
            return None
        return self.page * self.PAGE + self['rows'].getSelectedIndex()

    def row(self):
        index = self.index()
        return self.entries[index] if index is not None and index < len(self.entries) else None

    def focus(self):
        row = self.row()
        text, before, after = self.detail_callback(row) if row else ('Aucun élément', None, None)
        self['detail'].setText(text)
        for name, path in (('before', before), ('after', after)):
            widget = self[name]
            if path:
                self[name + '_label'].show()
            else:
                self[name + '_label'].hide()
            if widget.instance is None:
                continue
            if path and Path(path).is_file():
                widget.instance.setScale(1)
                widget.instance.setPixmapFromFile(str(path))
                widget.show()
            else:
                widget.hide()

    def turn_page(self, delta):
        if self.busy:
            return
        self.page = min(max(0, self.page+delta), max(0, (len(self.entries)-1)//self.PAGE))
        self.refresh()

    def toggle(self):
        index = self.index()
        if index is not None:
            if index in self.selected:
                self.selected.remove(index)
            else:
                self.selected.add(index)
            self.refresh()

    def toggle_all(self):
        self.selected = set() if len(self.selected) == len(self.entries) else set(range(len(self.entries)))
        self.refresh()

    def action(self, key):
        if self.busy:
            return
        if self.selectable and key == 'ok':
            self.toggle()
        elif self.selectable and key == 'yellow':
            self.toggle_all()
        elif self.callbacks.get(key):
            self.callbacks[key](self)
