import customtkinter as ctk
from tkinter import filedialog
import os
from pydpp.compiler import ProblemSet, ProblemSeverity, collect_errors
from pydpp.compiler.parser import parse
from pydpp.compiler.tokenizer import tokenize, TokenKind

ctk.set_appearance_mode("System")
ctk.set_default_color_theme(os.path.join(os.path.dirname(__file__), 'Metadata/style.json'))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Draw++")
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.after(0, lambda: self.state('zoomed'))

        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Draw++", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.new_file_but = ctk.CTkButton(self.sidebar_frame, text="nouveau fichier", command=self.new_tab)
        self.new_file_but.grid(row=1, column=0, padx=20, pady=10)
        self.bind("<Control-n>", lambda event: self.new_tab(event=event))

        self.import_but = ctk.CTkButton(self.sidebar_frame, text="importer", command=self.imp_event)
        self.import_but.grid(row=2, column=0, padx=20, pady=10)
        self.bind("<Control-o>", lambda event: self.imp_event(event))

        self.sup_but = ctk.CTkButton(self.sidebar_frame, text="supprimer", command=self.sup_tab)
        self.sup_but.grid(row=4, column=0, padx=20, pady=10)
        self.bind("<Control-w>", lambda event: self.sup_tab(event))

        self.save_but = ctk.CTkButton(self.sidebar_frame, text="sauvegarder", command=self.sauv_event)
        self.save_but.grid(row=3, column=0, padx=20, pady=10)
        self.bind("<Control-s>", lambda event: self.sauv_event(event))

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                      command=self.change_appearance_mode)
        self.appearance_mode_menu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.scaling_label = ctk.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                     command=self.change_scaling)
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        self.tabview = ctk.CTkTabview(self, width=250)
        self.tabview.grid(row=0, column=1, padx=10, pady=(10, 0), sticky="nsew")
        self.tabview.grid_columnconfigure(0, weight=1)
        self.tabview.add("Menu").grid_columnconfigure(0, weight=1)

        self.textboxes = {}  # Dict for tab-textboxes

        menu = ctk.CTkTextbox(self.tabview.tab("Menu"))
        self.textboxes["Menu"] = menu

        self.terminal = ctk.CTkTextbox(self)
        self.terminal.grid(row=1, column=1, padx=10, pady=(10, 0), sticky="nsew")

        # set default values
        self.appearance_mode_menu.set("System")
        self.scaling_optionemenu.set("100%")
        self.newfilecount = 1

    def change_appearance_mode(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def change_scaling(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)

    def text_search(self, cont):
        '''
        Text research function
        '''
        tab = self.tabview.get()
        text = self.textboxes[tab].get("1.0", "end-1c")
        if (cont in text):
            # return coordonnates. Multiple sets for each occurence
            return True
        else:
            return False

    def search(self, tab, cont):
        if self.textboxes[tab]:
            textbox = self.textboxes.get(tab)  # Get corresponding Textbox
            text = textbox.get("1.0", "end-1c")
            if (text == cont):
                return False  # False if file exists and True if it doesn't
            else:
                return True
        else:
            return True

    def sup_tab(self, event=None):
        tab = self.tabview.get()  # Get current tab
        if tab!="Menu":
            # Sets tab to previous tab in list, or last if the last one is closed
            self.tabview.set(list(self.textboxes)[self.tabview.index(tab) + (1 if len(list(self.textboxes)) != self.tabview.index(tab)+1 else -1)])
            self.tabview.delete(tab)
            self.textboxes.pop(tab)
            self.newfilecount -= 1
        else:
            print("impossible")

    def sup_reptab(self, tab):
        if tab:
            if tab != "Menu":
                self.tabview.delete(tab)
            else:
                print("impossible, nom de l'onglet: 'Menu'")
        else:
            print("impossible pas d'onglet")

    def sauv_event(self, event=None):
        tab = self.tabview.get()  # Get current oppened tab
        if tab != "Menu":
            textbox = self.textboxes.get(tab)  # Get corresponding Textbox
            if textbox:
                text = textbox.get("1.0", "end-1c")  # Get Textbox content
                file = filedialog.asksaveasfilename(filetypes=[("txt fichier", ".txt")], initialfile=tab)
                filename = os.path.basename(file)
                if file:
                    with open(file, "w") as f:
                        f.write(text)
                    if filename != tab:
                        if self.textboxes[filename]:
                            self.sup_reptab(filename)
                        self.tabview.rename(tab, filename)
                        self.textboxes[filename] = self.textboxes[tab]
                        self.textboxes.pop(tab)
                        self.tabview.set(filename)

    def imp_event(self, event=None):
        file = filedialog.askopenfilename(title="Importer",
                                          defaultextension=".txt",
                                          filetypes=[("txt fichier", ".txt")],
                                          initialdir=r"PROJET",
                                          # Mettre un r pour faire la diférence entre \ en tant que signe spécial et \ pour un caractère lambda
                                          )
        if file:
            file_name = os.path.basename(file)
            if file_name in self.textboxes:
                pass  # File is already oppened
            else:
                self.new_tab(file_name)
                fichier = open(file, "r")
                lecture = fichier.readlines()
                for line in lecture:
                    self.textboxes[file_name].insert("end", line)

    def new_tab(self, name: str = None, event=None):
        if not name:
            name = f"New file {self.newfilecount}"
            self.newfilecount += 1
        if name:
            self.tabview.add(name)
            self.tabview.tab(name).grid_columnconfigure(0, weight=1)
            self.tabview.tab(name).grid_rowconfigure(0, weight=1)
            showtext = ctk.CTkTextbox(self.tabview.tab(name))
            showtext.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

            self.init_highlighting(showtext)
            showtext.bind("<<Modified>>", lambda e: self.update_highlighting(showtext))

            self.textboxes[name] = showtext
            self.tabview.set(name)

    def init_highlighting(self, txt: ctk.CTkTextbox):
        # Configure all syntax highlighting tags
        txt.tag_config("kw", foreground="#268bd2")
        txt.tag_config("str", foreground="#cb4b16")
        txt.tag_config("num", foreground="#859900")
        txt.tag_config("err", underline=True, underlinefg="red")

        def err_enter(er):
            print("ERROR ENTER: cursor is at", txt.index("current"))
            # Then use that coordinate to find where the error is and show a tooltip... somehow

        def err_exit(er):
            v = txt.index("current")
            print(f"ERROR EXIT: cursor stepped away ({v} now)")

        # Bind some functions to run when the cursor enters or leaves an error in the text.
        # We can use that to show tooltips!
        txt.tag_bind("err", "<Enter>", err_enter)
        txt.tag_bind("err", "<Leave>", err_exit)

    def update_highlighting(self, txt: ctk.CTkTextbox):
        # Converts FileCoordinates into tkinter coordinates
        def tidx_to_tkidx(idx):
            return f"1.0+{idx}c"

        # Clear all existing highlighting
        txt.tag_remove("kw", "1.0", "end")
        txt.tag_remove("str", "1.0", "end")
        txt.tag_remove("num", "1.0", "end")
        txt.tag_remove("err", "1.0", "end")

        # Get the entire text of the textbox
        t = txt.get("1.0", "end")

        # Run the tokenizer (for primary syntax highlighting) and the parser (for error recognition)
        tkn_list = bench("tokenize:", lambda: tokenize(t))
        tree = bench("parse:", lambda: parse(tkn_list))  # not used yet, costly!

        # Highlight every portion of the text that matches with a token
        s = bench_start("highlighting")
        start = 0
        keywords = {x for x in TokenKind if x.name.startswith("KW") or x == TokenKind.LITERAL_BOOL}
        for t in tkn_list:
            l = len(t.full_text)
            if t.kind in keywords:
                # Keyword
                txt.tag_add("kw", tidx_to_tkidx(start), tidx_to_tkidx(start + l))
            elif t.kind == TokenKind.LITERAL_STRING:
                # String
                txt.tag_add("str", tidx_to_tkidx(start), tidx_to_tkidx(start + l))
            elif t.kind == TokenKind.LITERAL_NUM:
                # Number
                txt.tag_add("num", tidx_to_tkidx(start), tidx_to_tkidx(start + l))
            start += l
        bench_end(s)

        # Highlight every error (not warnings for now)
        def f():
            ps = ProblemSet()
            collect_errors(tree, ps)
            for e in ps.grouped[ProblemSeverity.ERROR]:
                txt.tag_add("err", tidx_to_tkidx(e.pos.start), tidx_to_tkidx(e.pos.end))

        bench("error finding", f)

        # Set modified to False so the event triggers again (it's dumb but that's how it works)
        txt.edit_modified(False)

import time
def bench(name, func):
    start_time = time.perf_counter_ns()
    res = func()
    end_time = time.perf_counter_ns()

    elapsed_time_ms = (end_time - start_time) / 1_000_000
    print(f"{name}: {elapsed_time_ms} ms")
    return res

def bench_start(name):
    start_time = time.perf_counter_ns()
    print(f"{name}... ", end="")
    return start_time

def bench_end(start_time):
    end_time = time.perf_counter_ns()
    elapsed_time_ms = (end_time - start_time) / 1_000_000
    print(f"{elapsed_time_ms} ms")

if __name__ == "__main__":
    app = App()
    app.mainloop()
