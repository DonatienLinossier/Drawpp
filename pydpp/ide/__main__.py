#import pydpp.compiler as comp

import tkinter
import tkinter.messagebox
import customtkinter

from pydpp.compiler import ProblemSet, ProblemSeverity
from pydpp.compiler.parser import parse
from pydpp.compiler.tokenizer import tokenize, TokenKind

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        self.title("CustomTkinter complex_example.py")
        self.geometry(f"{1100}x{580}")

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Draw++", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_button_sauv = customtkinter.CTkButton(self.sidebar_frame, text="sauvegarder", command=self.sauv_event)
        self.sidebar_button_sauv.grid(row=1, column=0, padx=20, pady=10)

        self.sidebar_button_imp = customtkinter.CTkButton(self.sidebar_frame, text= "importer",command=self.imp_event)
        self.sidebar_button_imp.grid(row=2, column=0, padx=20, pady=10)

        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.set_default_color_theme_label=customtkinter.CTkLabel(self.sidebar_frame, text="theme:", anchor="w")
        self.set_default_color_theme_label.grid(row=4, column=0, padx=20, pady=(10,0))
        self.set_default_color_theme_optionmenu=customtkinter.CTkOptionMenu(self.sidebar_frame, values=["blue", "dark-blue", "green"],
                                                                       command=self.change_theme_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                               command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        # create main entry and button
        self.entry = customtkinter.CTkEntry(self, placeholder_text="CTkEntry")
        self.entry.grid(row=3, column=1, columnspan=2, padx=(20, 0), pady=(20, 20), sticky="nsew")

        self.main_button_1 = customtkinter.CTkButton(master=self, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
        self.main_button_1.grid(row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # create textbox
        self.textbox = customtkinter.CTkTextbox(self, width=250)
        self.textbox.grid(row=0, column=1, rowspan=2 , padx=(20, 0), pady=(20, 0), sticky="nsew")

        # create tabview
        self.tabview = customtkinter.CTkTabview(self, width=250)
        self.tabview.grid(row=0, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.tabview.add("CTkTabview")
        self.tabview.add("Tab 2")
        self.tabview.add("Tab 3")
        self.tabview.tab("CTkTabview").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs
        self.tabview.tab("Tab 2").grid_columnconfigure(0, weight=1)

        self.optionmenu_1 = customtkinter.CTkOptionMenu(self.tabview.tab("CTkTabview"), dynamic_resizing=False,
                                                        values=["Value 1", "Value 2", "Value Long Long Long"])
        self.optionmenu_1.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.combobox_1 = customtkinter.CTkComboBox(self.tabview.tab("CTkTabview"),
                                                    values=["Value 1", "Value 2", "Value Long....."])
        self.combobox_1.grid(row=1, column=0, padx=20, pady=(10, 10))
        self.string_input_button = customtkinter.CTkButton(self.tabview.tab("CTkTabview"), text="Open CTkInputDialog",
                                                           command=self.open_input_dialog_event)
        self.string_input_button.grid(row=2, column=0, padx=20, pady=(10, 10))
        self.label_tab_2 = customtkinter.CTkLabel(self.tabview.tab("Tab 2"), text="CTkLabel on Tab 2")
        self.label_tab_2.grid(row=0, column=0, padx=20, pady=20)


        # set default values
        self.appearance_mode_optionemenu.set("Dark")
        self.scaling_optionemenu.set("100%")
        self.optionmenu_1.set("CTkOptionmenu")
        self.combobox_1.set("CTkComboBox")
        self.textbox.insert("0.0", "CTkTextbox\n\n" + "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.\n\n" * 20)

        # --- SYNTAX HIGHILIGHTING ---
        # Initialize color tags
        self.init_highlighting(self.textbox)
        # Bind the Modified event to update the syntax highlighting on type/paste/delete/etc.
        self.textbox.bind("<<Modified>>", lambda e: self.update_highlighting(self.textbox))
        # Change font of textbox because existing one is UGLY
        # Try all monospace fonts I know so it works on both Windows and Linux.
        fonts = tkinter.font.families()
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
        self.textbox.configure(font=customtkinter.CTkFont(family=fam, size=13))

    def open_input_dialog_event(self):
        dialog = customtkinter.CTkInputDialog(text="Type in a number:", title="CTkInputDialog")
        print("CTkInputDialog:", dialog.get_input())

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_theme_mode_event(self, newtheme: str):
        customtkinter.set_default_color_theme(newtheme)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def sidebar_button_event(self):
        print("sidebar_button click")

    def sauv_event(self):
        print("je download le fichier")

    def imp_event(self):
        print("j'importe le fichier")
        self.tabview.add("Tab ajouté")

    def init_highlighting(self, txt: customtkinter.CTkTextbox):
        # Configure all syntax highlighting tags
        txt.tag_config("kw", foreground="#268bd2")
        txt.tag_config("str", foreground="#cb4b16")
        txt.tag_config("num", foreground="#859900")
        txt.tag_config("err", underline=True, underlinefg="red")

        def err_enter(er):
            print("ERROR ENTER: cursor is at", txt.index("current"))
            # Then use that coordinate to find where the error is and show a tooltip... somehow

        def err_exit(er):
            print(f"ERROR EXIT: cursor stepped away ({txt.index("current")} now)")

        # Bind some functions to run when the cursor enters or leaves an error in the text.
        # We can use that to show tooltips!
        txt.tag_bind("err", "<Enter>", err_enter)
        txt.tag_bind("err", "<Leave>", err_exit)

    def update_highlighting(self, txt: customtkinter.CTkTextbox):
        # Converts FileCoordinates into tkinter coordinates
        def fc_to_idx(fc):
            return f"{fc.line}.{fc.column-1}"

        # Clear all existing highlighting
        txt.tag_remove("kw", "1.0", "end")
        txt.tag_remove("str", "1.0", "end")
        txt.tag_remove("num", "1.0", "end")
        txt.tag_remove("err", "1.0", "end")

        # Get the entire text of the textbox
        t = txt.get("1.0", "end")

        # Run the tokenizer (for primary syntax highlighting) and the parser (for error recognition)
        ps = ProblemSet() # Errors will be there
        tkn_list = tokenize(t, ps)
        tree = parse(tkn_list, ps) # not used yet, costly!

        # Highlight every portion of the text that matches with a token
        for t in tkn_list:
            if t.kind.name.startswith("KW") or t.kind == TokenKind.LITERAL_BOOL:
                # Keyword
                txt.tag_add("kw", fc_to_idx(t.pos.start), fc_to_idx(t.pos.end))
            elif t.kind == TokenKind.LITERAL_STRING:
                # String
                txt.tag_add("str", fc_to_idx(t.pos.start), fc_to_idx(t.pos.end))
            elif t.kind == TokenKind.LITERAL_NUM:
                # Number
                txt.tag_add("num", fc_to_idx(t.pos.start), fc_to_idx(t.pos.end))

        # Highlight every error (not warnings for now)
        for e in ps.grouped[ProblemSeverity.ERROR]:
            txt.tag_add("err", fc_to_idx(e.pos.start), fc_to_idx(e.pos.end))

        # Set modified to False so the event triggers again (it's dumb but that's how it works)
        txt.edit_modified(False)


if __name__ == "__main__":
    app = App()
    app.mainloop()
