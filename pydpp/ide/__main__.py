import sys
import typing
from os import mkdir

import customtkinter as ctk
from tkinter import filedialog, font
import os
from pydpp.compiler import ProblemSet, ProblemSeverity, collect_errors, analyse, semantic
from pydpp.compiler.parser import parse
from pydpp.compiler.tokenizer import tokenize, TokenKind, AuxiliaryKind
from pydpp.compiler import compile_code
import subprocess

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

        menu = ctk.CTkTextbox(self.tabview.tab("Menu"), font=ctk.CTkFont(size=17))
        menu.pack(expand=True, fill="both") #let the textbox be visible in "Menu"
        self.textboxes["Menu"] = menu #let the tab be in the dictionnary

        syntax_path = os.path.join(os.path.dirname(__file__), "../../Syntaxe de Draw++.txt")
        # Put the entirety of the file in the textbox
        try:
            with open(syntax_path, "r", encoding="utf-8") as f:
                menu.insert("end", f.read())
        except:
            print("Failed to load syntax file.")
            pass
            # Too bad!

        for f in semantic.builtin_funcs.values():
            func_sig = f.name + "(" + ", ".join([p.type.value + " " + p.name for p in f.parameters ]) + ")"
            menu.insert("end", func_sig)
            if f.doc is not None:
                menu.insert("end", "\nDocumentation : " + f.doc + "\n")
            menu.insert("end", "\n")

        menu.configure(state="disabled")    #disable the access to Menu to anyone (if modification to "Menu", first type meu.config(state="normal") and pls replace this line when you're done) 
        self.terminal = ctk.CTkTextbox(self, state="disabled") #creation of the terminal
        self.terminal.grid(row=1, column=1, padx=10, pady=(10, 0), sticky="nsew")

        # set default values
        self.appearance_mode_menu.set("System")
        self.scaling_optionemenu.set("100%")
        self.newfilecount = 1
        self.tt = ToolTip(self)

    def tidx_to_tkidx(self, idx):
            return f"1.0+{idx}c"

    def run_program(self, event=None, preview_c_code=False):
        """
        Tries to compile the code, and compiles it if no error has been detected.
        Otherwise prints every error in the terminal and allow the user to access the error with a simple double-click action
        """

        tab_name = self.tabview.get()

        # Cleans terminal
        self.delete_terminal()
        self.write_to_terminal(f"{tab_name} is compiling...")

        # Retrieves code from the file and tries to compiles it
        code = self.textboxes[tab_name].get("0.0", ctk.END)

        # Make up all paths necessary for compilation
        exe_suffix = ".exe" if os.name == "nt" else "" # Add the .exe suffix on windows
        exe_path = f"./dpp-build/{tab_name}" + exe_suffix # Make the executable path
        c_path = f"./dpp-build/{tab_name}.c" # Same for the C file

        # Create the dpp-build folder if it doesn't exist
        if not os.path.exists("./dpp-build"):
            mkdir("./dpp-build")

        # Compile! Now!
        okay, problems, c_file = compile_code(code, exe_path, c_path)

        # Reads every problem to add a pointer to the error in the code itself
        for p in (problems):

            # Retrieves info about the error
            if p.pos is not None:
                # We do have position info, let's make a clickable link to see the where the error is.
                s = p.pos.start
                e = p.pos.end
                start, end = self.tidx_to_tkidx(str(s)), self.tidx_to_tkidx(str(e))
                t = str(s)+"."+str(e)

                # Creates a new tag with a pointer to the error in the code
                self.terminal.tag_config(t, underline=True, foreground="blue")
                self.terminal.tag_bind(t, "<Button-1>", lambda event, pos=end: self.get_to_text(textbx, pos))
                x=len(t) +37
                print(x)
                x=str(x)+"c"
                print(x)
                x="end-"+x
                # Writes to the terminal the error message
                self.write_to_terminal(f"{p} (double clique pour acceder)")
                textbx = self.textboxes[self.tabview.get()]

                # Sets the tag to highlight the location of the value
                self.terminal.tag_add(str(t), x , "end-30c")
            else:
                # No position information! (Must be a compile/toolchain error).
                self.write_to_terminal(f"{p}")
        
        # The code can be compiled
        if not preview_c_code:
            # Run the app only if compilation was a success
            if okay:
                # Run the app in the background
                subprocess.Popen(exe_path)
        else:
            # Try to show the C code using the system's text editor, if there's a c file to begin with
            if c_file is not None and os.path.exists(c_file):
                fallback_editor = "notepad" if sys.platform == "win32" else "gedit"
                subprocess.Popen([os.getenv("EDITOR", fallback_editor), c_file])

    def get_to_text(self, txt, index, event=None):
        '''
        Sets cursor at location of the index of the textbox
        '''
        txt.mark_set("insert", index)
        txt.see(index)
        txt.focus_force()

    def write_to_terminal(self, text):
        '''
        Simply writes something to ther terminal
        '''
        self.terminal.configure(state="normal")
        self.terminal.insert(ctk.END, f"\n{str(text)}")
        self.terminal.configure(state="disabled")

    def delete_terminal(self):
        '''
        Deletes everything written in the terminal
        '''
        self.terminal.configure(state="normal")
        self.terminal.delete("0.0", ctk.END)
        self.terminal.configure(state="disabled")

    def sup_tab(self, event=None):
        tab = self.tabview.get()  # Get current tab
        if tab!="Menu":
            # Sets tab to previous tab in list, or last if the last one is closed
            self.tabview.set(list(self.textboxes)[self.tabview.index(tab) + (1 if len(list(self.textboxes)) != self.tabview.index(tab)+1 else -1)])
            self.tabview.delete(tab)
            self.textboxes.pop(tab)
        else:
            self.write_to_terminal("impossible")

    def sup_reptab(self, tab):
        if tab:
            if tab != "Menu":
                self.tabview.delete(tab)
            else:
                self.write_to_terminal("impossible, nom de l'onglet: 'Menu'")
        else:
            self.write_to_terminal("impossible pas d'onglet")

    def sauv_event(self, event=None):
        tab = self.tabview.get()  # Get current oppened tab
        if tab != "Menu":
            textbox = self.textboxes.get(tab)  # Get corresponding Textbox
            if textbox:
                text = textbox.get("1.0", "end-1c")  # Get Textbox content
                file = filedialog.asksaveasfilename(
                    defaultextension="*.dpp",
                    filetypes=[("dpp","*.dpp")],
                    initialfile=((tab + ".dpp") if not tab.endswith(".dpp") else tab)
                    )
                filename = os.path.basename(file)
                if file:
                    with open(file, "w") as f:
                        f.write(text)
                    if filename != tab:
                        if filename in self.textboxes:
                            self.sup_reptab(filename)
                        self.tabview.rename(tab, filename)
                        self.textboxes[filename] = self.textboxes[tab]
                        self.textboxes.pop(tab)
                        self.tabview.set(filename)

    def imp_event(self, event=None):
        file = filedialog.askopenfilename(title="Importer",
                                        defaultextension="*.dpp",
                                        filetypes=[("dpp","*.dpp")],
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

            # Make the compile & run buttons, organized horizontally
            buttons_frame = ctk.CTkFrame(self.tabview.tab(name))
            code_button = ctk.CTkButton(buttons_frame, text="Voir le code C",
                                                       command=lambda: self.run_program(preview_c_code=True))
            code_button.pack(side="left", padx=10)
            run_button = ctk.CTkButton(buttons_frame, text="Lancer le programme",
                                                      command=lambda: self.run_program())
            run_button.pack(side="left")

            buttons_frame.grid(row=0, column=0, sticky="ne")
            showtext = ctk.CTkTextbox(self.tabview.tab(name), undo=True)
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
            showtext.configure(font=ctk.CTkFont(family=fam, size=15))

            self.textboxes[name] = showtext
            self.tabview.set(name)

    def init_highlighting(self, txt: ctk.CTkTextbox):
        # Configure all syntax highlighting tags
        txt.tag_config("kw", foreground="#268bd2")
        txt.tag_config("str", foreground="#cb4b16")
        txt.tag_config("num", foreground="#859900")
        txt.tag_config("cmt", foreground="#93a1a1")
        txt.tag_config("err", underline=True, underlinefg="red")

        def err_enter(er):

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

            self.tt.destroy()

            # Then use that coordinate to find where the error is and show a tooltip... somehow.
            # It's there !!

            # Gather all error messages, separated with a newline, by looking at err_indices
            msg = "\n".join([txt.drawpp_error_infos[i].message for i in err_indices])

            # Gather all suggestions, by adding them in a list of tuples:
            #     (suggestion title, function to apply the suggestion)
            sug = []
            for i in err_indices:
                # Find the Problem object
                pb = txt.drawpp_error_infos[i]
                if pb.suggestion is not None:
                    # We do have a suggestion for this!
                    # Make up an apply function specifically for this problem.
                    def apply(e, real_problem=pb, pb_sug=pb.suggestion):
                        # Destroy the tooltip first.
                        self.tt.destroy()

                        # Find the root node (the Program)
                        root = real_problem.node
                        while root.parent is not None:
                            root = root.parent

                        # Apply the suggestion
                        pb_sug.apply(real_problem.node)

                        # Replace the ENTIRETY of the code with the one modified by the suggestion.
                        # Keep the cursor as it was before.
                        cursor = txt.index("insert")
                        txt.delete("1.0", "end")
                        txt.insert("1.0", root.full_text)
                        txt.mark_set("insert", cursor)
                        txt.see(cursor)

                        # Make sure the file is reparsed correctly.
                        txt.edit_modified(True)

                    # Append it to the list of suggestions
                    sug.append(("Appliquer la suggestion : " + pb.suggestion.title, apply))

            # Find where to place the textbox. We're going to place it below the character.
            box = txt.bbox("current")
            if box is None:
                # We can't find it??? Use the pointer coordinates instead.
                x, y = txt.winfo_pointerxy()
            else:
                # box is a tuple of (glyph_x, glyph_y, glyph_width, glyph_height)
                # Calculate the coordinates so we get the textbox below the character.
                # Also add a bit of constant offsets so it looks nicer.
                x, y = box[0] + txt.winfo_rootx() + box[2] + 5, box[1] + txt.winfo_rooty() + box[3] + 10

            # Show the tooltip with the message and the suggestions
            self.tt.showtip(msg, x, y, sug)

        def err_exit(er):
             self.tt.become_independent()

        # Bind some functions to run when the cursor enters or leaves an error in the text.
        # We can use that to show tooltips!
        txt.tag_bind("err", "<Enter>", err_enter)
        txt.tag_bind("err", "<Leave>", err_exit)

        # Add a "drawpp_error_infos" attribute to our textbox, with a list that acts as a map.
        # This attribute is used to register additional info for each problem underlined in the text,
        # so we can show it in the tooltip.
        # ==> drawpp_error_infos[i] = problem data for text with tag "err_info_{i}"
        setattr(txt, "drawpp_error_infos", [])

    def update_highlighting(self, txt: ctk.CTkTextbox):
        # Converts a string index into tkinter coordinates
        def tidx_to_tkidx(idx):
            return f"1.0+{idx}c"

        # Clear all existing highlighting
        for tag in txt.tag_names(): # tag_names() returns all tags in the textbox
            txt.tag_remove(tag, "1.0", "end")

        # Reset errors we've saved before
        txt.drawpp_error_infos = []

        # Close the tooltip if it's opened.
        self.tt.destroy()

        # Get the entire text of the textbox
        code_text = txt.get("1.0", "end")

        # Run the tokenizer (for primary syntax highlighting)
        tkn_list = profile("tokenize", lambda: tokenize(code_text))

        # Highlight every portion of the text that matches with a token
        s = profile_start("highlighting")
        start = 0
        keywords = {x for x in TokenKind if x.name.startswith("KW") or x == TokenKind.LITERAL_BOOL}
        for t in tkn_list:
            # First look at auxiliary text to highlight comments
            for a in t.pre_auxiliary:
                l = len(a.text)
                if a.kind == AuxiliaryKind.SINGLE_LINE_COMMENT:
                    # Comment
                    txt.tag_add("cmt", tidx_to_tkidx(start), tidx_to_tkidx(start + l))
                start += l

            l = len(t.text)
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

        # Now, let's parse the tree to find any errors; and do semantic analysis for bonus errors
        tree = profile("parse", lambda: parse(tkn_list))
        semantic = profile("semantic", lambda: analyse(tree))

        # Highlight every error (not warnings for now)
        s = profile_start("error finding")
        ps = ProblemSet()
        # Collect all errors from the tree, and put them all in the problem set
        collect_errors(tree, ps, True, semantic)
        i = 0
        for e in ps.grouped[ProblemSeverity.ERROR]:
            # When the span is of zero-length, extend it on the right by one character to indicate something
            # that is "missing".
            ps, pe = e.pos.start, e.pos.end
            if ps == pe:
                if pe < len(code_text) and code_text[pe] != "\n":
                    pe = pe + 1
                else:
                    # Tkinter doesn't support highlighting at the very end of line.
                    # So, in this case, let's just extend to the left.
                    ps = ps - 1

            # Convert coordinates to tkinter coordinates
            start, end = tidx_to_tkidx(ps), tidx_to_tkidx(pe)

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

    def __init__(self, widget):
        self.widget = widget
        "The window root widget."
        self.tipwindow = None
        "The currently shown window tooltip frame."
        self.independent = False
        "When the tooltip should be on its own (i.e. the span is not hovered anymore). When it is"
        self.x = 0
        "X offset (window coordinates)"
        self.y = 0
        "Y offset (window coordinates)"

        self.stay_open_range = 25
        "How much pixels the cursor can move away from the tooltip before it closes, when it's independent."

        # Bind the motion event to close the tooltip if the cursor is too far away
        self.widget.bind("<Motion>", self.motion, add="+")

    def showtip(self, text,  x: int, y: int, sug: list[tuple[str, typing.Callable]]=[]):
        "Display text in tooltip window"
        if self.tipwindow:
            # Already shown!
            return

        self.tipwindow = tw = ctk.CTkToplevel(self.widget, fg_color=ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        self.x = x
        self.y = y
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))

        # Create an inner frame so we can add padding
        inner_frame = ctk.CTkFrame(tw)

        # Make the label for the problem messages
        label = ctk.CTkLabel(inner_frame, text=text, justify=ctk.LEFT)
        label.pack(ipadx=1, fill=ctk.X) # Pack it -> https://python-course.eu/tkinter/layout-management-in-tkinter.php

        # Add "apply suggestion" links for each suggestion
        for sug, action in sug:
            sug_label = ctk.CTkLabel(inner_frame, text=sug, justify=ctk.LEFT, text_color="#23AFE9",
                                     font=ctk.CTkFont(weight="bold", underline=True))
            sug_label.bind("<Button-1>", action)
            sug_label.pack(ipadx=1, fill=ctk.X)

        # Add some padding to the inner frame.
        inner_frame.pack(padx=5, pady=5)

    def destroy(self):
        # Destroys the tooltip window. Also resets independence.
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None
        self.independent = False

    def motion(self, event):
        # The cursor has moved, see if we should close the tool tip
        if self.independent and self.tipwindow:
            self.close_if_cursor_too_far()

    def become_independent(self):
        # The cursor has left the error span, we're now independent!
        # From now on, we'll check if the cursor is inside the tooltip (or near it), and if it's not
        # we'll close it.
        if self.tipwindow:
            self.independent = True
            self.close_if_cursor_too_far()

    def close_if_cursor_too_far(self):
        # Do some boring math to calculate the local coordinates of the cursor on the tooltip's space.
        ptr_x, ptr_y = self.widget.winfo_pointerxy()

        my_x, my_y = self.x, self.y
        my_width, my_height = self.tipwindow.winfo_width(), self.tipwindow.winfo_height()

        local_x, local_y = ptr_x - my_x, ptr_y - my_y

        b = self.stay_open_range
        # See if we're B pixels too far on the horizontal or vertical axis (not Euclidean distance)
        if local_x < -b or local_x > my_width + b or local_y < -b or local_y > my_height + b:
            self.destroy()

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
