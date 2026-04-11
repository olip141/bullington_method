import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
import os

# ==========================================
# KLASA DO OBSŁUGI DYMKÓW Z PODPOWIEDZIAMI
# ==========================================
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 10
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True) # Usuwa domyślną ramkę Windows
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("Arial", 9, "normal"), padx=5, pady=5)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# ==========================================
# GŁÓWNA APLIKACJA
# ==========================================
class BullingtonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Kalkulator strat metodą Bullingtona")
        self.root.geometry("1200x850")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.df = None

        # BAZA TRAS
        '''
        Biłgoraj 22.721786 50.543981
        Nowa dęba 21.751556 50.412893
        abka-Zdrój 19.958645 49.607263 
        Nowu Sącz 20.714326 49.614761
        Kasina Wielka 20.098887 49.712232
        Kluszkowce 20.315843 49.455830 
        '''

        self.routes_db = {
            "Własna trasa": {"dist": "0", "h_ter_tx": "0", "h_ter_rx": "0", "csv_path": ""},
            "Nowa Dęba – Biłgoraj": {"dist": "0", "h_ter_tx": "0", "h_ter_rx": "0", "csv_path": "nowa_deba.csv"},
            "Rabka Zdrój – Nowy Sącz": {"dist": "0", "h_ter_tx": "0", "h_ter_rx": "0", "csv_path": "rabka.csv"},
            "Kasina Wielka – Kluszkowice": {"dist": "0", "h_ter_tx": "0", "h_ter_rx": "0", "csv_path": "kasina.csv"}
        }

        # mnPANEL BOCZNY
        self.sidebar = tk.Frame(root, width=400, bg="#f4f4f4", padx=15, pady=10)
        self.sidebar.pack(side="left", fill="y")

        # Wybór Trasy
        tk.Label(self.sidebar, text="1. WYBIERZ TRASĘ", font=("Arial", 11, "bold"), bg="#f4f4f4").pack(pady=(0, 5))
        self.route_var = tk.StringVar()
        self.route_cb = ttk.Combobox(self.sidebar, textvariable=self.route_var, state="readonly")
        self.route_cb['values'] = list(self.routes_db.keys())
        self.route_cb.current(0)
        self.route_cb.pack(fill="x", pady=2)
        self.route_cb.bind("<<ComboboxSelected>>", self.update_route_fields)

        # Parametry Łącza
        tk.Label(self.sidebar, text="\n2. PARAMETRY ŁĄCZA", font=("Arial", 11, "bold"), bg="#f4f4f4").pack(pady=5)

        self.entries = {}
        tk.Label(self.sidebar, text="Częstotliwość [MHz]", bg="#f4f4f4").pack(anchor="w")
        self.freq_cb = ttk.Combobox(self.sidebar)
        self.freq_cb['values'] = ["230", "410", "860", "1800", "2400", "5800"]
        self.freq_cb.insert(0, "860")
        self.freq_cb.pack(fill="x", pady=2)
        self.entries['freq'] = self.freq_cb

        # podział na teren i maszt + teksty dymków
        fields = [
            ("Teren Tx [m n.p.m.] (Auto z pliku)", "h_ter_tx", "210", ""),
            ("Wysokość zawieszenia anteny nadawczej Tx nad gruntem [m]", "h_ant_tx", "20", ""),
            ("Teren Rx [m n.p.m.] (Auto z pliku)", "h_ter_rx", "230", ""),
            ("Wysokość zawieszenia anteny nadawczej Rx nad gruntem [m]", "h_ant_rx", "20", ""),
            ("Całkowita odległość [km] (Auto z pliku)", "dist", "70.184", ""),
            ("Współczynnik k (krzywizna Ziemi)", "k", "1.333", "Współczynnik refrakcji atmosferycznej.\n• k = 1.333: Standardowa, kulista Ziemia.\n• k = 9999: Wyłącza krzywiznę (Płaska Ziemia).")
        ]

        for label_text, key, default, tooltip_text in fields:
            # Ramka na tekst i znak zapytania
            lbl_frame = tk.Frame(self.sidebar, bg="#f4f4f4")
            lbl_frame.pack(fill="x", anchor="w")
            
            lbl = tk.Label(lbl_frame, text=label_text, bg="#f4f4f4", fg="#333333" if "Auto" in label_text else "black")
            lbl.pack(side="left")
            
            if tooltip_text:
                info_icon = tk.Label(lbl_frame, text=" (?)", font=("Arial", 10, "bold"), fg="#0078D7", bg="#f4f4f4", cursor="hand2")
                info_icon.pack(side="left")
                ToolTip(info_icon, tooltip_text)

            entry = tk.Entry(self.sidebar)
            entry.insert(0, default)
            entry.pack(fill="x", pady=2)
            self.entries[key] = entry

        # Zidentyfikowane Szczyty (z dymkiem)
        sec3_frame = tk.Frame(self.sidebar, bg="#f4f4f4")
        sec3_frame.pack(fill="x", pady=(15, 5))
        
        tk.Label(sec3_frame, text="3. ZIDENTYFIKOWANE SZCZYTY", font=("Arial", 11, "bold"), bg="#f4f4f4").pack(side="left")
        info3 = tk.Label(sec3_frame, text=" (?)", font=("Arial", 10, "bold"), fg="#0078D7", bg="#f4f4f4", cursor="hand2")
        info3.pack(side="left")
        ToolTip(info3, "Wysokość tych szczytów (h) ZAWIERA już poprawkę na wybrzuszenie Ziemi.\nDlatego ich wartość jest wyższa, niż wprost odczytana z pliku/mapy.")

        manual_frame = tk.Frame(self.sidebar, bg="#f4f4f4")
        manual_frame.pack(fill="x")
        tk.Label(manual_frame, text="d [km]", bg="#f4f4f4", width=10).grid(row=0, column=1)
        tk.Label(manual_frame, text="h [m n.p.m]", bg="#f4f4f4", width=10).grid(row=0, column=2)
        
        self.manual_points = []
        for i in range(1, 5):
            tk.Label(manual_frame, text=f"P{i}:", bg="#f4f4f4").grid(row=i, column=0)
            d_ent = tk.Entry(manual_frame, width=10)
            h_ent = tk.Entry(manual_frame, width=10)
            d_ent.grid(row=i, column=1, padx=2, pady=2)
            h_ent.grid(row=i, column=2, padx=2, pady=2)
            self.manual_points.append((d_ent, h_ent))

        # Akcje
        tk.Label(self.sidebar, text="\n4. AKCJE", font=("Arial", 11, "bold"), bg="#f4f4f4").pack(pady=5)
        tk.Button(self.sidebar, text="Wgraj CSV (Piast)", command=self.load_csv_dialog, bg="#0078D7", fg="white").pack(fill="x", pady=2)
        tk.Button(self.sidebar, text="OBLICZ I GENERUJ RAPORT", command=self.run_calculations, bg="#28a745", fg="white", font=("Arial", 10, "bold")).pack(fill="x", pady=5)
        
        # Przycisk zapisu do pliku
        tk.Button(self.sidebar, text="ZAPISZ WYKRES DO PLIKU", command=self.save_plot, bg="#ffc107", fg="black", font=("Arial", 10, "bold")).pack(fill="x", pady=2)

        # Wyniki z dymkiem
        self.res_var = tk.StringVar(value="Straty: --- dB")
        res_frame = tk.Frame(self.sidebar, bg="#d4edda")
        res_frame.pack(fill="x", pady=(10, 0))
        
        res_lbl = tk.Label(res_frame, textvariable=self.res_var, font=("Arial", 13, "bold"), fg="#155724", bg="#d4edda", pady=5)
        res_lbl.pack(side="left", padx=(5, 0))
        
        info_res = tk.Label(res_frame, text=" (?)", font=("Arial", 10, "bold"), fg="#0078D7", bg="#d4edda", cursor="hand2")
        info_res.pack(side="left")
        ToolTip(info_res, "Parametr v: miara wnikania przeszkody w I strefę Fresnela.\nLd: ostateczne straty dyfrakcyjne w decybelach.")


        # --- PANEL GŁÓWNY (WYKRES) ---
        self.main_panel = tk.Frame(root, bg="white")
        self.main_panel.pack(side="right", expand=True, fill="both")
        self.fig, self.ax = plt.subplots(figsize=(7, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_panel)
        self.canvas.get_tk_widget().pack(expand=True, fill="both")

    def on_closing(self):
        self.root.quit()
        self.root.destroy()
        sys.exit()

    def update_route_fields(self, event):
        route_name = self.route_var.get()
        if route_name in self.routes_db:
            data = self.routes_db[route_name]
            
            self.entries['dist'].delete(0, tk.END)
            self.entries['dist'].insert(0, data['dist'])
            self.entries['h_ter_tx'].delete(0, tk.END)
            self.entries['h_ter_tx'].insert(0, data['h_ter_tx'])
            self.entries['h_ter_rx'].delete(0, tk.END)
            self.entries['h_ter_rx'].insert(0, data['h_ter_rx'])
            
            # Auto wczytywanie pliku jeśli jest w folderze
            if data['csv_path'] and os.path.exists(data['csv_path']):
                self.process_csv(data['csv_path'], silent=True)
                self.run_calculations()

    def load_csv_dialog(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.process_csv(file_path, silent=False)

    def process_csv(self, file_path, silent=False):
        try:
            temp_df = pd.read_csv(file_path, sep=None, decimal=',', engine='python', encoding='utf-8-sig')
            temp_df.columns = [c.strip() for c in temp_df.columns]
            
            col_dist = "Distance from Tx [km]"
            col_elev = "Terrain height [m a.s.l.]"
            
            if col_dist in temp_df.columns and col_elev in temp_df.columns:
                self.df = temp_df[[col_dist, col_elev]].rename(columns={col_dist: "distance", col_elev: "elevation"})
                
                # --- AUTO-UZUPEŁNIANIE Z CSV ---
                d_total = self.df['distance'].max()
                h_t_tx = self.df['elevation'].iloc[0]
                h_t_rx = self.df['elevation'].iloc[-1]

                self.entries['dist'].delete(0, tk.END)
                self.entries['dist'].insert(0, f"{d_total:.3f}")
                self.entries['h_ter_tx'].delete(0, tk.END)
                self.entries['h_ter_tx'].insert(0, f"{h_t_tx:.1f}")
                self.entries['h_ter_rx'].delete(0, tk.END)
                self.entries['h_ter_rx'].insert(0, f"{h_t_rx:.1f}")
                
                if not silent:
                    messagebox.showinfo("Sukces", "Załadowano profil terenu i zaktualizowano wysokości bazy!")
            else:
                if not silent: messagebox.showerror("Błąd", "Nie znaleziono kolumn z Piasta.")
        except Exception as e:
            if not silent: messagebox.showerror("Błąd", f"Błąd wczytywania: {e}")

    def save_plot(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png", 
                                                 filetypes=[("PNG files", "*.png"), 
                                                            ("JPEG files", "*.jpg"), 
                                                            ("Wszystkie pliki", "*.*")])
        if file_path:
            try:
                self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Sukces", f"Wykres został zapisany pomyślnie w:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się zapisać pliku:\n{e}")

    def run_calculations(self):
        try:
            f = float(self.entries['freq'].get().replace(',', '.'))
            
            # --- SUMOWANIE TERENU I ANTENY ---
            ter_tx = float(self.entries['h_ter_tx'].get().replace(',', '.'))
            ant_tx = float(self.entries['h_ant_tx'].get().replace(',', '.'))
            h_tx_val = ter_tx + ant_tx
            
            ter_rx = float(self.entries['h_ter_rx'].get().replace(',', '.'))
            ant_rx = float(self.entries['h_ant_rx'].get().replace(',', '.'))
            h_rx_val = ter_rx + ant_rx
            
            D_total = float(self.entries['dist'].get().replace(',', '.'))
            k = float(self.entries['k'].get().replace(',', '.'))
            
            calc_df = None
            if self.df is not None:
                calc_df = self.df.copy()
                calc_df['earth_curve'] = (calc_df['distance'] * (D_total - calc_df['distance'])) / (12.75 * k)
                calc_df['h_adj'] = calc_df['elevation'] + calc_df['earth_curve']

                valid_peaks = calc_df[(calc_df['distance'] > 0.05) & (calc_df['distance'] < D_total - 0.05)]
                top_4 = valid_peaks.sort_values(by='h_adj', ascending=False).head(4).sort_values(by='distance')
                
                for i, (_, row) in enumerate(top_4.iterrows()):
                    self.manual_points[i][0].delete(0, tk.END)
                    self.manual_points[i][0].insert(0, f"{row['distance']:.3f}")
                    self.manual_points[i][1].delete(0, tk.END)
                    self.manual_points[i][1].insert(0, f"{row['h_adj']:.2f}")
            else:
                pts = []
                for d_ent, h_ent in self.manual_points:
                    d_txt, h_txt = d_ent.get().replace(',', '.'), h_ent.get().replace(',', '.')
                    if d_txt and h_txt:
                        pts.append({'distance': float(d_txt), 'elevation': float(h_txt)})
                if not pts:
                    messagebox.showwarning("Brak danych", "Wgraj CSV lub wpisz punkty P1-P4 ręcznie!")
                    return
                calc_df = pd.DataFrame(pts).sort_values(by='distance')
                
                # Zastosowanie krzywizny Ziemi dla punktów wpisanych ręcznie
                calc_df['earth_curve'] = (calc_df['distance'] * (D_total - calc_df['distance'])) / (12.75 * k)
                calc_df['h_adj'] = calc_df['elevation'] + calc_df['earth_curve']

            valid_df = calc_df[(calc_df['distance'] > 0.001) & (calc_df['distance'] < D_total - 0.001)]
            if valid_df.empty: return

            # OBLICZANIE NACHYLEŃ I IDENTYFIKACJA PUNKTÓW 
            s1_series = (valid_df['h_adj'] - h_tx_val) / valid_df['distance']
            s2_series = (valid_df['h_adj'] - h_rx_val) / (D_total - valid_df['distance'])

            s1_max = s1_series.max()
            s2_max = s2_series.max()

            idx_s1 = s1_series.idxmax()
            idx_s2 = s2_series.idxmax()

            tx_horizon_dist = valid_df.loc[idx_s1, 'distance']
            tx_horizon_elev = valid_df.loc[idx_s1, 'h_adj']
            rx_horizon_dist = valid_df.loc[idx_s2, 'distance']
            rx_horizon_elev = valid_df.loc[idx_s2, 'h_adj']

            print("PUNKTY OPARCIA HORYZONTU")
            print(f"[Tx] Horyzont od nadajnika oparł się o punkt:")
            print(f"     -> Dystans: {tx_horizon_dist:.3f} km | Wysokość: {tx_horizon_elev:.2f} m")
            print(f"[Rx] Horyzont od odbiornika oparł się o punkt:")
            print(f"     -> Dystans: {rx_horizon_dist:.3f} km | Wysokość: {rx_horizon_elev:.2f} m")
        
            db = (h_rx_val - h_tx_val + s2_max * D_total) / (s1_max + s2_max)
            hb = h_tx_val + s1_max * db
            h_los = h_tx_val + (h_rx_val - h_tx_val) / D_total * db
            h_clearance = hb - h_los

            wavelength = 299.79 / f
            v = h_clearance * np.sqrt((2 / wavelength) * (1 / (db * 1000) + 1 / ((D_total - db) * 1000)))
            loss = 0 if v <= -0.7 else 6.9 + 20 * np.log10(np.sqrt((v - 0.1)**2 + 1) + v - 0.1)

            self.res_var.set(f"Straty: {loss:.2f} dB  |  v = {v:.3f}")

            top_pts = top_4 if self.df is not None else None
            self.plot_results(calc_df, D_total, h_tx_val, h_rx_val, db, hb, loss, top_pts)

        except Exception as e:
            messagebox.showerror("Błąd", f"Wystąpił błąd podczas obliczeń: {e}")

    def plot_results(self, df, D, h_tx, h_rx, db, hb, loss, top_pts=None):
        self.ax.clear()
        self.ax.fill_between(df['distance'], df['h_adj'], color='#8d6e63', alpha=0.3, label='Profil terenu ')
        self.ax.plot(df['distance'], df['h_adj'], color='#5d4037', lw=1.5)
        self.ax.plot([0, D], [h_tx, h_rx], color='blue', linestyle='--', label='Linia widoczności (LOS)')
        self.ax.plot(db, hb, 'ro', markersize=9, label='Ostrze Bullingtona')
        self.ax.vlines(db, ymin=min(h_tx, h_rx)-50, ymax=hb, color='red', linestyles='dotted')
        
        if top_pts is not None and not top_pts.empty:
            self.ax.scatter(top_pts['distance'], top_pts['h_adj'], marker='x', color='yellow', s=100, zorder=5, label='Wykryte 4 szczyty')

        self.ax.set_title(f"Profil Dyfrakcyjny Bullingtona (Straty = {loss:.2f} dB)")
        self.ax.set_xlabel("Odległość [km]")
        self.ax.set_ylabel("Wysokość całkowita [m n.p.m.]")
        self.ax.legend(fontsize='small')
        self.ax.grid(True, alpha=0.4)
        self.canvas.draw()

if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    app = BullingtonApp(root)
    root.mainloop()