import customtkinter as ctk
from tkinter import filedialog, font
import os
from pydpp.compiler import ProblemSet, ProblemSeverity, collect_errors
from pydpp.compiler.parser import parse
from pydpp.compiler.tokenizer import tokenize, TokenKind
from pydpp.compiler import compile_code

ctk.set_appearance_mode("System")
ctk.set_default_color_theme(os.path.join(os.path.dirname(__file__), 'Metadata/style.json'))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Draw++")
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        if os.name == "nt":
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

        self.terminal = ctk.CTkTextbox(self, state="disabled")
        self.terminal.grid(row=1, column=1, padx=10, pady=(10, 0), sticky="nsew")

        # set default values
        self.appearance_mode_menu.set("System")
        self.scaling_optionemenu.set("100%")
        self.newfilecount = 1
        self.tt = None

    def run_program(self, event=None):
        """
        get code compile it and return good or bad execution.
        Return coords of error if detected, maybe add a link to point directly in the file (the correct one)
        """
        self.delete_terminal()
        self.write_to_terminal(f"{self.tabview.get()} is compiling... I don't if it works though")
        # Call function and return something
        code_to_exe = self.textboxes[self.tabview.get()].get("0.0", ctk.END)
        # Not implemented yet
        # self.write_to_terminal(compile_code(code_to_exe))

        # POC for error at execution and redirect in code
        index_err = "5.7"
        self.write_to_terminal(f"test at {index_err} (double click to access)")
        textbx = self.textboxes[self.tabview.get()]
        self.terminal.tag_config("err", underline=True, foreground="blue")
        self.terminal.tag_bind("err", "<Button-1>", lambda event: self.get_to_text(textbx, index_err))
        self.terminal.tag_add("err", "3.8", "3.11")


    def get_to_text(self, txt, index, event=None):
        txt.mark_set("insert", index)
        txt.see(index)
        txt.focus_force()

    def write_to_terminal(self, text):
        self.terminal.configure(state="normal")
        self.terminal.insert(ctk.END, f"\n{str(text)}")
        self.terminal.configure(state="disabled")

    def delete_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete("0.0", ctk.END)
        self.terminal.configure(state="disabled")

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
                file=filedialog.asksaveasfilename(
                    defaultextension="*.txt",
                    filetypes=[("txt","*.txt")],
                    initialfile=tab
                    )
                filename =os.path.basename(file)
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
                                        defaultextension="*.txt",
                                        filetypes=[("txt","*.txt")],
                                        initialdir= r"PROJET", # Mettre un r pour faire la diférence entre \ en tant que signe spécial et \ pour un caractère lambda
                                        )   
        if file:    
            file_name=os.path.basename(file)
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
            self.tabview.tab(name).grid_rowconfigure((1), weight=1)
            self.run_button = ctk.CTkButton(self.tabview.tab(name), text="Run file", command= lambda : self.run_program())
            self.run_button.grid(row=0, column=0, sticky="ne")
            showtext = ctk.CTkTextbox(self.tabview.tab(name))
            showtext.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
            showtext.focus_set()

            # --- SYNTAX HIGHILIGHTING ---
            # Initialize color tags
            self.init_highlighting(showtext)
            # Bind the Modified event to update the syntax highlighting on type/paste/delete/etc.
            showtext.bind("<<Modified>>", lambda e: self.update_highlighting(showtext))
            # Change font of textbox because existing one is UGLY
            # Try all monospace fonts I know so it works on both Windows and Linux.
            fonts = font.families()
            if "Cascadia Code" in fonts:
                fam = "Cascadia Code"
            elif "Consolas" in fonts:
                fam = "Consolas"
            elif "Ubuntu Mono" in fonts:
                fam = "Ubuntu Mono"
            elif "Noto Mono" in fonts:
                fam = "Noto Mono"
            elif "Liberation Mono" in fonts:
                fam = "Liberation Mono"
            elif "Lucida Console" in fonts:
                fam = "Lucida Console"
            else:
                fam = fonts[0]
            showtext.configure(font=ctk.CTkFont(family=fam, size=13))

            self.textboxes[name] = showtext
            self.tabview.set(name)

    def init_highlighting(self, txt: ctk.CTkTextbox):
        # Configure all syntax highlighting tags
        txt.tag_config("kw", foreground="#268bd2")
        txt.tag_config("str", foreground="#cb4b16")
        txt.tag_config("num", foreground="#859900")
        txt.tag_config("err", underline=True, underlinefg="red")

        def err_enter(er):
            # print("ERROR ENTER: cursor is at", txt.index("current"))

            # The cursor is on the error. Let's find the err_info_{i} tag, and grab that i value
            # to find the problem data.
            # To do this, we need to go through all tags spanning this character, and find the err_info_{i} tag.
            # We *may* have multiple error spanning one character, so get them all!
            err_indices = []
            for tag in txt.tag_names(txt.index("current")):
                # Is it an error info tag?
                if tag.startswith("err_info_"):
                    # Yep, skip the "err_info" part and get the index.
                    err_indices.append(int(tag[len("err_info_"):]))

            # Then use that coordinate to find where the error is and show a tooltip... somehow.
            # It's there !!
            if not self.tt:
                # Gather all error messages, separated with a newline, by looking at err_indices
                msg = "\n".join([txt.drawpp_error_infos[i].message for i in err_indices])
                self.tt = createToolTip(txt, msg, self.winfo_pointerx() - self.winfo_rootx(), self.winfo_pointery() - self.winfo_rooty())

        def err_exit(er):
            # print(f"ERROR EXIT: cursor stepped away ({txt.index("current")} now)")
            if self.tt:
                self.tt.destroy()
                self.tt = None

        # Bind some functions to run when the cursor enters or leaves an error in the text.
        # We can use that to show tooltips!
        txt.tag_bind("err", "<Enter>", err_enter)
        txt.tag_bind("err", "<Leave>", err_exit)

        # Add a "drawpp_error_infos" attribute to our textbox, with a list that acts as a map.
        # This attribute is used to register additional info for each problem underlined in the text,
        # so we can show it in the tooltip.
        # ==> drawpp_error_infos[i] = problem data for text with tag "err_info_{i}"
        setatCtr(txt, "drawpp_error_infos", [])

    def update_highlighting(self, txt: ctk.CTkTextbox):
        # Converts a string index into tkinter coordinates
        def tidx_to_tkidx(idx):
            return f"1.0+{idx}c"

        # Clear all existing highlighting
        for tag in txt.tag_names(): # tag_names() returns all tags in the textbox
            txt.tag_remove(tag, "1.0", "end")

        # Reset errors we've saved before
        txt.drawpp_error_infos = []

        # Get the entire text of the textbox
        t = txt.get("1.0", "end")

        # Run the tokenizer (for primary syntax highlighting)
        tkn_list = profile("tokenize", lambda: tokenize(t))

        # Highlight every portion of the text that matches with a token
        s = profile_start("highlighting")
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
        profile_end(s)

        # Now, let's parse the tree to find any errors
        tree = profile("parse", lambda: parse(tkn_list))

        # Highlight every error (not warnings for now)
        s = profile_start("error finding")
        ps = ProblemSet()
        # Collect all errors from the tree, and put them all in the problem set
        collect_errors(tree, ps)
        i = 0
        for e in ps.grouped[ProblemSeverity.ERROR]:
            # Convert coordinates to tkinter coordinates
            start, end = tidx_to_tkidx(e.pos.start), tidx_to_tkidx(e.pos.end)

            # Add the "err" tag for red underlining
            txt.tag_add("err", start, end)

            # Add the "err_info_{i}" tag used for fetching the problem info (description),
            # and add the problem in a drawpp_error_infos list.
            txt.tag_add(f"err_info_{i}", start, end)
            txt.drawpp_error_infos.append(e)
            i += 1
        profile_end(s)

        if ENABLE_PROFILING:
            print("---")

        # Set modified to False so the event triggers again (it's dumb but that's how it works)
        txt.edit_modified(False)

    def change_appearance_mode(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def change_scaling(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)


class ToolTip(object):

    def __init__(self, widget, x_offset: int, y_offset: int):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.x_offset = x_offset + 20
        self.y_offset = y_offset + 30

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        self.tipwindow = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (self.x_offset, self.y_offset))
        label = ctk.CTkLabel(tw, text=self.text, justify=ctk.LEFT)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

    def destroy(self):
        if self.tipwindow:
            self.tipwindow.destroy()

def createToolTip(widget, text, x: int, y: int):
    toolTip = ToolTip(widget, x, y)
    toolTip.showtip(text)
    return toolTip

# Temporary functions to profile the perf of highlighting updates
import time
import os
ENABLE_PROFILING = os.getenv("DRAWPP_PROFILE", "0") == "1"
def profile(name, func):
    if not ENABLE_PROFILING:
        return func()

    start_time = time.perf_counter_ns()
    res = func()
    end_time = time.perf_counter_ns()

    elapsed_time_ms = (end_time - start_time) / 1_000_000
    print(f"{name}: {elapsed_time_ms} ms")
    return res

def profile_start(name):
    if not ENABLE_PROFILING:
        return 0

    start_time = time.perf_counter_ns()
    print(f"{name}: ", end="")
    return start_time

def profile_end(start_time):
    if not ENABLE_PROFILING:
        return

    end_time = time.perf_counter_ns()
    elapsed_time_ms = (end_time - start_time) / 1_000_000
    print(f"{elapsed_time_ms} ms")

if __name__ == "__main__":
    app = App()
    app.mainloop()
