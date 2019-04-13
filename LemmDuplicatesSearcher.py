#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import collections
import functools
import morfeusz2
import os
import re
import tkinter as tk
from nltk.collocations import BigramCollocationFinder
from nltk.corpus import stopwords
from nltk.metrics import BigramAssocMeasures
from nltk.tokenize import WordPunctTokenizer
from tkinter import ttk, messagebox, scrolledtext


LABELS_NAME = {'cancel': "Anuluj",
               'copy': "Kopiuj",
               'cut': "Wytnij",
               'delete': "Usuń",
               'dupllist': "Lista duplikatów:",
               'err': "Błąd",
               'insert': "Wstaw tekst:",
               'notsearched': "nie szukano",
               'paste': "Wklej",
               'selall': "Zaznacz wszystko",
               'softdupl': "Duplikaty znalezione na podstawie lemmatyzacji",
               'sort': "Szukaj",
               'sorted': "Posortowana lista słów:",
               'strictdupl': "Duplikaty ścisłe"}
ERRORS_MSG = {'input': "W tekście znajdują się niedozwolone znaki lub nie "
                       "wprowadzono żadnego tekstu"}


class AppCore:
    """ Model """

    def __init__(self):
        self._text = None
        self._tokenized = None  # type List
        self._lemmatized = None  # type List
        self._strict_dupl = None  # type List
        self._lemm_dupl = None  # type List

    def strip_text(self, s):
        """Usuwa z tekstu interpunkcję."""
        pattern = re.compile(r"[\W_-]")
        text = pattern.sub(" ", s)
        return text

    def sort_ascend(self, alist):
        """Sortuje listę alfabetycznie, według klucza: najpierw małe litery,
        potem duże.
        """
        sortedlist = sorted(alist,
                            key=lambda w: (w.upper(), w.swapcase()))
        return sortedlist

    def tokenize_into_words(self, text):
        """Dzieli tekst na tokeny."""
        wpt = WordPunctTokenizer()
        tokens = wpt.tokenize(text)
        return tokens

    def lemmatize(self, text):
        """Szuka lemmatów słów w danym tekście. Zwraca słownik zbudowany wg
        schemtu `lemmat: formy występujące w tekście`.
        """
        morf = morfeusz2.Morfeusz(whitespace=morfeusz2.SKIP_WHITESPACES,
                                  generate=False)
        analysis = morf.analyse(text)
        pairs = [(
            lemm[2][0],  # forma występująca w tekście
            lemm[2][1].split(":")[0],  # lemmat
        )
            for lemm in analysis]
        lemmas = collections.defaultdict(set)
        for key, val in pairs:
            lemmas[key].add(val)
        return lemmas

    def search_lemm_dupl(self, tokens, adict):
        """Zwraca set zawierający liste zduplikowanych słow. Przy szukaniu
        duplikatów porównuje lemmaty słowa."""
        dupl = []
        for key, val in adict.items():
            val.add(key)
            d = [x for x in val if x in tokens]
            if len(d) > 1:
                dupl.extend(d)
        return set(dupl)

    def search_strict_dupl(self, alist):
        """Zwraca posortowaną liste zduplikowanych slow. Przy szukaniu
        duplikatow ma znaczenie rozmiar liter. Szuka tylko `ścisłych duplikatów`.
        """
        duplset = set([x for x in alist if alist.count(x) > 1])
        dupllist = list(duplset)
        return self.sort_ascend(dupllist)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, s):
        self._text = self.strip_text(s)

    @property
    def tokenized(self):
        return self._tokenized

    @property
    def lemmatized(self):
        self._lemmatized = self.lemmatize(self._text)
        return self._lemmatized

    @property
    def strict_dupl(self):
        self._tokenized = self.tokenize_into_words(self._text)
        return self.search_strict_dupl(self._tokenized)

    @property
    def lemm_dupl(self):
        return self.search_lemm_dupl(self._tokenized, self._lemmatized)


class AppControl:
    """ Controller """

    def __init__(self):
        self.model = AppCore()
        self.create_gui()

    def create_gui(self):
        self.view = AppGui()
        self.view.register(self)
        self.view.mainloop()

    def run(self):
        outmsg = []
        outtext = []
        input_text = self.view.input_text
        if not input_text.strip():
            self.view.showerr()
            return
        self.model.text = input_text
        lemmatized = self.model.lemmatized
        self.view.fill_listbox(lemmatized)
        strict_dupl = self.model.strict_dupl
        outtext += strict_dupl
        outmsg.append(len(strict_dupl))
        self.view.highlight_elem(strict_dupl, 'strict')
        lemmdupl = self.model.lemm_dupl
        self.view.highlight_elem(lemmdupl, 'lemm')
        outtext += lemmdupl
        outmsg.append(len(lemmdupl))
        outtext = self.model.sort_ascend(set(outtext))
        self.view.insert_output(outtext)


class AppGui:
    """ View """

    col = {'strict': '#ccffe6', 'lemm': '#00b33c'}

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(os.path.splitext(os.path.basename(__file__))[0])
        self.controller = None
        self.selected = None
        self.lbls = LABELS_NAME
        self.errmsg = ERRORS_MSG
        self.create_gui()
        self.create_popup_menu()

    def register(self, controller):
        self.controller = controller

    def mainloop(self):
        self.root.mainloop()

    @property
    def input_text(self):
        return self.scrolltext.get('1.0', tk.END)

    def create_inputfield(self):
        frame = ttk.Frame(self.root, padding=5)
        ttk.Label(frame, text=self.lbls['insert']).pack(fill=tk.X, pady=(10, 0))
        self.scrolltext = tk.scrolledtext.ScrolledText(frame,
                                                       height=10, wrap=tk.WORD)
        self.scrolltext.pack(expand=1, fill=tk.BOTH)
        frame.pack(expand=1, fill=tk.BOTH, side=tk.TOP)
        self.scrolltext.bind("<Button-3>", self.show_popup_menu)
        self.scrolltext.bind("<Control-a>", self.select_all)

    def create_listbox(self):
        frame = ttk.Frame(self.root, padding=5)
        ttk.Label(frame,
                  text=self.lbls['sorted']).pack(fill=tk.X, pady=(10, 0))
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox = tk.Listbox(frame)
        self.listbox.pack(expand=1, fill=tk.BOTH, side=tk.TOP)
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)
        frame.pack(expand=1, fill=tk.BOTH, side=tk.TOP)

    def create_outputfield(self):
        frame = ttk.Frame(self.root, padding=5)
        ttk.Label(frame,
                  text=self.lbls['dupllist']).pack(fill=tk.X, pady=(10, 0))
        self.scrolltext_out = tk.scrolledtext.ScrolledText(frame,
                                                           height=10,
                                                           wrap=tk.WORD)
        self.scrolltext_out.pack(expand=1, fill=tk.BOTH)
        frame.pack(expand=1, fill=tk.BOTH, side=tk.TOP)
        self.scrolltext_out.bind("<Button-3>", self.show_popup_menu)

    def create_statusbar(self):
        self.statusmsg0 = tk.StringVar()
        self.statusmsg1 = tk.StringVar()

        frame = ttk.Frame(self.root, padding=5)

        ttk.Label(frame,
                  text=self.lbls['strictdupl'],
                  background=self.col['strict']).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(frame,
                  text=self.lbls['softdupl'],
                  foreground=self.col['lemm']).pack(side=tk.LEFT, padx=(0, 5))
        frame.pack(expand=0, fill=tk.BOTH, side=tk.TOP)

    def create_button(self):
        frame = ttk.Frame(self.root, padding=5)
        ttk.Button(frame,
                   command=self._quit,
                   text=self.lbls['cancel'],
                   width=10).pack(side=tk.RIGHT)
        ttk.Button(frame,
                   command=self.run,
                   text=self.lbls['sort'],
                   width=10).pack(side=tk.RIGHT)
        frame.pack(expand=0, fill=tk.BOTH, side=tk.TOP)

    def create_gui(self):
        self.create_inputfield()
        self.create_listbox()
        self.create_outputfield()
        self.create_statusbar()
        self.create_button()

    def create_popup_menu(self):
        self.popup_menu = tk.Menu(self.root, tearoff=0)

        self.popup_menu.add_command(label=self.lbls['cut'],
                                    accelerator="Ctrl+X",
                                    command=lambda: self.cut(self.selected))
        self.popup_menu.add_command(label=self.lbls['copy'],
                                    accelerator="Ctrl+C",
                                    command=lambda: self.copy(self.selected))
        self.popup_menu.add_command(label=self.lbls['paste'],
                                    accelerator="Ctrl+V",
                                    command=lambda: self.mypaste(self.selected))
        self.popup_menu.add_command(label=self.lbls['delete'],
                                    accelerator="Delete",
                                    command=lambda: self.cut(self.selected))
        self.popup_menu.add_separator()
        self.popup_menu.add_command(label=self.lbls['selall'],
                                    accelerator="Ctrl+A",
                                    command=lambda:
                                        self.select_all(self.selected))

    def cut(self, event=None):
        event.event_generate("<<Cut>>")
        return "break"

    def copy(self, event=None):
        event.event_generate("<<Copy>>")
        return "break"

    def mypaste(self, event=None):
        # https://stackoverflow.com/a/46636970
        try:
            event.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
        event.insert(tk.INSERT, event.clipboard_get())
        event.event_generate("<<Paste>>")
        return "break"

    def show_popup_menu(self, event):
        self.selected = event.widget
        self.popup_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def select_all(self, event=None):
        # event.tag_add(tk.SEL, '1.0', tk.END)
        self.scrolltext.tag_add(tk.SEL, '1.0', tk.END)
        return "break"

    def fill_listbox(self, alist):
        self.listbox.delete(0, tk.END)
        for elem in alist:
            self.listbox.insert(tk.END, elem)

    def highlight_elem(self, iterable, elem_type):
        for i in range(self.listbox.size()):
            if self.listbox.get(i) in iterable:
                if elem_type == "strict":
                    self.listbox.itemconfig(i, background=self.col[elem_type])
                else:
                    self.listbox.itemconfig(i, foreground=self.col[elem_type])

    def insert_output(self, out):
        self.scrolltext_out.delete('0.0', tk.END)
        self.scrolltext_out.insert(tk.END, '\n'.join(out))

    def showerr(self):
        msg = self.errmsg['input']
        messagebox.showerror(title=self.lbls['err'], message=msg)

    def run(self):
        self.controller.run()

    def _quit(self):
        self.root.quit()
        self.root.destroy()


def main():
    AppControl()


if __name__ == "__main__":
    main()
