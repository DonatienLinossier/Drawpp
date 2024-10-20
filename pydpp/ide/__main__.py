#import pydpp.compiler as comp

import tkinter
import tkinter.messagebox
import customtkinter
from tkinter import filedialog
import os
customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme('Drawpp/pydpp/ide/Metadata/style.json')  # Themes: "blue" (standard), "green", "dark-blue"


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        self.title("Draw++")
        self.geometry(f"{1100}x{580}")

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure(0, weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Draw++", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_button_NewF = customtkinter.CTkButton(self.sidebar_frame, text="nouveau fichier", command=self.new_tab)
        self.sidebar_button_NewF.grid(row=1, column=0, padx=20, pady=10)

        self.sidebar_button_imp = customtkinter.CTkButton(self.sidebar_frame, text= "importer",command=self.imp_event)
        self.sidebar_button_imp.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar_button_sauv = customtkinter.CTkButton(self.sidebar_frame, text="sauvegarder", command=self.sauv_event)
        self.sidebar_button_sauv.grid(row=3, column=0, padx=20, pady=10)

        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.set_default_color_theme_optionmenu=customtkinter.CTkOptionMenu(self.sidebar_frame, values=["blue", "dark-blue", "green"],
                                                                       command=self.change_theme_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                               command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        # create main entry and button
        self.entry = customtkinter.CTkEntry(self, placeholder_text="ctk")
        self.entry.grid(row=3, column=1, columnspan=2, padx=(20, 0), pady=(20, 20), sticky="nsew")


        # create tabview
        self.tabview = customtkinter.CTkTabview(self, width=250)
        self.tabview.grid(row=0, column=1, padx=10, pady=(10, 0), sticky="nsew")
        self.tabview.grid_columnconfigure(0, weight=1)
        self.tabview.add("Menu").grid_columnconfigure(0, weight=1)

        self.textboxes = {} #liste de références de textbox pour les tab

        text=customtkinter.CTkTextbox(self.tabview.tab("Menu")) #création de la textbox du tab Menu
        text.insert("1.0","Ici les règles et commandes") #Ne marche pas pour l'instant
        self.textboxes["Menu"] = text #rajout de la textbox à la liste de textbox



        # set default values
        self.appearance_mode_optionemenu.set("Dark")
        self.scaling_optionemenu.set("100%")
        
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
        tab = self.tabview.get()  # Connaitre le nom du tab ouvert actuellement
        if tab!="Menu":
            textbox = self.textboxes.get(tab)  # Récupérer la Textbox correspondante

            if textbox:
                text = textbox.get("1.0", "end-1c")  # Récupérer le contenu de la Textbox
                print(f"Contenu du textbox dans le tab '{tab}':", text)
                file=filedialog.asksaveasfilename(defaultextension=".txt", #type par défaut
                                            filetypes=[("txt fichier",".txt"),("pdf fichier",".pdf")], #possible d'ouvir (et donc impossible d'ouvrir les autres si il est créé)et agit en tuples (nombre de tuples infini max) dans une liste
                                            initialfile=tab
                                            )
                if file:
                    with open(file, "w") as f:
                        f.write(text)   

    def imp_event(self):
        file= filedialog.askopenfilename(title="Importer", #titre
                                        defaultextension=".txt", #type par défaut
                                        filetypes=[("txt fichier",".txt"),("pdf fichier",".pdf")], #possible d'ouvir (et donc impossible d'ouvrir les autres si il est créé)et agit en tuples (nombre de tuples infini max) dans une liste
                                        initialdir= r"PROJET", #endroit où on est redirigé de base pour ouvrir un fichier (mettre un r pour faire la diférence entre \ en tant que signe spécial et \ pour un caractère lambda)
                                        )   
        if file:    
            file_name=os.path.basename(file)
            if file_name=="Menu":
                while(file_name=="Menu"):
                    questionname = customtkinter.CTkInputDialog(text="Entrez le nom du nouveau fichier:", title="Nouveau fichier")
                    file_name=questionname.get_input()

            self.new_tab(file_name)
            fichier=open(file, "r") #ouverture du fichier en mode lecture
            lecture=fichier.readlines() #lecture du fichier
            for line in lecture:
                self.textboxes[file_name].insert("end", line) #insertion du text dans la textbox ligne par ligne
    
    def new_tab(self, name : str = None, event=None):
        print(name)
        if not name:
            questionname = customtkinter.CTkInputDialog(text="Entrez le nom du nouveau fichier:", title="Nouveau fichier")
            name=questionname.get_input()
            if name=="Menu":
                    while(name=="Menu"):
                        questionname = customtkinter.CTkInputDialog(text="Entrez le nom du nouveau fichier:", title="Nouveau fichier")
                        name=questionname.get_input()
        if name:
            self.tabview.add(name).grid_columnconfigure(0, weight=1)
            self.tabview.tab(name).grid_rowconfigure(0, weight=1)
            showtext=customtkinter.CTkTextbox(self.tabview.tab(name))  
            showtext.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")        
            self.textboxes[name] = showtext #ajout de la référence de la textbox dans la liste des références

if __name__ == "__main__":
    app = App()
    app.mainloop()
