import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
import os
import csv

def resource_path(relative_path):
    """ Zwraca bezwzględną ścieżkę do plików, działa dla skryptu .py i dla pliku .exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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

class BullingtonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Kalkulator strat metodą Bullingtona")
        self.root.geometry("1200x850")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.df = None # Teraz to bedzie slownik z numpy arrays

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
            ("Teren Tx [m n.p.m.] (Auto z pliku)", "h_ter_tx", "0", ""),
            ("Wysokość zawieszenia anteny nadawczej Tx nad gruntem [m]", "h_ant_tx", "0", ""),
            ("Teren Rx [m n.p.m.] (Auto z pliku)", "h_ter_rx", "0", ""),
            ("Wysokość zawieszenia anteny nadawczej Rx nad gruntem [m]", "h_ant_rx", "0", ""),
            ("Całkowita odległość [km] (Auto z pliku)", "dist", "0", ""),
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

        # Zidentyfikowane Szczyty 
        sec3_frame = tk.Frame(self.sidebar, bg="#f4f4f4")
        sec3_frame.pack(fill="x", pady=(15, 5))
        
        tk.Label(sec3_frame, text="3. ZIDENTYFIKOWANE SZCZYTY", font=("Arial", 11, "bold"), bg="#f4f4f4").pack(side="left")
        info3 = tk.Label(sec3_frame, text=" (?)", font=("Arial", 10, "bold"), fg="#0078D7", bg="#f4f4f4", cursor="hand2")
        info3.pack(side="left")
        ToolTip(info3, "Wysokość  szczytów (h) zawiera poprawkę na wybrzuszenie Ziemi.\nDlatego ich wartość jest wyższa, niż odczytana z pliku=.")

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
        tk.Button(self.sidebar, text="Wgraj CSV z profilem terenu z piast.edu.pl", command=self.load_csv_dialog, bg="#0078D7", fg="white").pack(fill="x", pady=2)
        tk.Button(self.sidebar, text="OBLICZ", command=self.run_calculations, bg="#28a745", fg="white", font=("Arial", 10, "bold")).pack(fill="x", pady=5)
        
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


        # WYKRES
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
            
            # Auto wczytywanie wbudowanego pliku
            if data['csv_path']:
                actual_path = resource_path(data['csv_path'])
                if os.path.exists(actual_path):
                    self.process_csv(actual_path, silent=True)
                    self.run_calculations()

    def load_csv_dialog(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.process_csv(file_path, silent=False)

    def process_csv(self, file_path, silent=False):
        try:
            distances = []
            elevations = []
            col_dist_idx = -1
            col_elev_idx = -1
            
            with open(file_path, mode='r', encoding='utf-8-sig') as file:
                # Automatyczna detekcja separatora dla CSV
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample)
                except csv.Error:
                    dialect = csv.excel
                    dialect.delimiter = ',' if ',' in sample else ';'
                
                reader = csv.reader(file, dialect)
                
                # Zczytywanie nagłówków
                headers = next(reader)
                headers = [h.strip() for h in headers]
                
                col_dist = "Distance from Tx [km]"
                col_elev = "Terrain height [m a.s.l.]"
                
                if col_dist in headers and col_elev in headers:
                    col_dist_idx = headers.index(col_dist)
                    col_elev_idx = headers.index(col_elev)
                else:
                    if not silent: messagebox.showerror("Błąd", "Nie znaleziono kolumn z Piasta.")
                    return

                # Parsowanie danych
                for row in reader:
                    if len(row) > max(col_dist_idx, col_elev_idx):
                        try:
                            # Obsluga przecinka dziesietnego
                            d_val = float(row[col_dist_idx].replace(',', '.'))
                            e_val = float(row[col_elev_idx].replace(',', '.'))
                            distances.append(d_val)
                            elevations.append(e_val)
                        except ValueError:
                            continue

            if distances and elevations:
                self.df = {
                    'distance': np.array(distances),
                    'elevation': np.array(elevations)
                }
                
                #AUTO-UZUPEŁNIANIE Z CSV
                d_total = self.df['distance'].max()
                h_t_tx = self.df['elevation'][0]
                h_t_rx = self.df['elevation'][-1]

                self.entries['dist'].delete(0, tk.END)
                self.entries['dist'].insert(0, f"{d_total:.3f}")
                self.entries['h_ter_tx'].delete(0, tk.END)
                self.entries['h_ter_tx'].insert(0, f"{h_t_tx:.1f}")
                self.entries['h_ter_rx'].delete(0, tk.END)
                self.entries['h_ter_rx'].insert(0, f"{h_t_rx:.1f}")
                
                if not silent:
                    messagebox.showinfo("Sukces", "Załadowano profil terenu i zaktualizowano wysokości bazy!")
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
            
            # SUMOWANIE TERENU I ANTENY
            ter_tx = float(self.entries['h_ter_tx'].get().replace(',', '.'))
            ant_tx = float(self.entries['h_ant_tx'].get().replace(',', '.'))
            h_tx_val = ter_tx + ant_tx
            
            ter_rx = float(self.entries['h_ter_rx'].get().replace(',', '.'))
            ant_rx = float(self.entries['h_ant_rx'].get().replace(',', '.'))
            h_rx_val = ter_rx + ant_rx
            
            D_total = float(self.entries['dist'].get().replace(',', '.'))
            k = float(self.entries['k'].get().replace(',', '.'))
            
            calc_dist = None
            calc_elev = None

            if self.df is not None:
                calc_dist = self.df['distance']
                calc_elev = self.df['elevation']
                earth_curve = (calc_dist * (D_total - calc_dist)) / (12.75 * k)
                h_adj = calc_elev + earth_curve

                # Wykrywanie 4 szczytow (z uzyciem numpy)
                # Filtrowanie brzegow
                valid_mask_peaks = (calc_dist > 0.05) & (calc_dist < D_total - 0.05)
                valid_dist_peaks = calc_dist[valid_mask_peaks]
                valid_adj_peaks = h_adj[valid_mask_peaks]

                if len(valid_adj_peaks) > 0:
                    # Znalezienie indeksow 4 najwiekszych (jesli jest mniej to wszystkich)
                    num_peaks = min(4, len(valid_adj_peaks))
                    idx_top4 = np.argsort(valid_adj_peaks)[-num_peaks:]
                    
                    # Sortowanie wg dystansu
                    top_dist = valid_dist_peaks[idx_top4]
                    top_adj = valid_adj_peaks[idx_top4]
                    sort_idx = np.argsort(top_dist)
                    
                    for i in range(4):
                        self.manual_points[i][0].delete(0, tk.END)
                        self.manual_points[i][1].delete(0, tk.END)
                        if i < num_peaks:
                            self.manual_points[i][0].insert(0, f"{top_dist[sort_idx[i]]:.3f}")
                            self.manual_points[i][1].insert(0, f"{top_adj[sort_idx[i]]:.2f}")
            else:
                pts_dist = []
                pts_elev = []
                for d_ent, h_ent in self.manual_points:
                    d_txt, h_txt = d_ent.get().replace(',', '.'), h_ent.get().replace(',', '.')
                    if d_txt and h_txt:
                        pts_dist.append(float(d_txt))
                        pts_elev.append(float(h_txt))
                if not pts_dist:
                    messagebox.showwarning("Brak danych", "Wgraj CSV lub wpisz punkty P1-P4 ręcznie!")
                    return
                
                # Sortowanie
                sort_idx = np.argsort(pts_dist)
                calc_dist = np.array(pts_dist)[sort_idx]
                calc_elev = np.array(pts_elev)[sort_idx]
                
                earth_curve = (calc_dist * (D_total - calc_dist)) / (12.75 * k)
                h_adj = calc_elev + earth_curve

            valid_mask = (calc_dist > 0.001) & (calc_dist < D_total - 0.001)
            if not np.any(valid_mask): return
            
            valid_dist = calc_dist[valid_mask]
            valid_h_adj = h_adj[valid_mask]

            # OBLICZANIE NACHYLEŃ I IDENTYFIKACJA PUNKTÓW 
            s1_series = (valid_h_adj - h_tx_val) / valid_dist
            s2_series = (valid_h_adj - h_rx_val) / (D_total - valid_dist)

            s1_max = np.max(s1_series)
            s2_max = np.max(s2_series)

            idx_s1 = np.argmax(s1_series)
            idx_s2 = np.argmax(s2_series)

            tx_horizon_dist = valid_dist[idx_s1]
            tx_horizon_elev = valid_h_adj[idx_s1]
            rx_horizon_dist = valid_dist[idx_s2]
            rx_horizon_elev = valid_h_adj[idx_s2]

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

            # Zbieranie punktow do wykresu
            top_pts = None
            if self.df is not None:
                top_pts_x = []
                top_pts_y = []
                for i in range(4):
                    d_txt = self.manual_points[i][0].get()
                    h_txt = self.manual_points[i][1].get()
                    if d_txt and h_txt:
                        top_pts_x.append(float(d_txt.replace(',','.')))
                        top_pts_y.append(float(h_txt.replace(',','.')))
                if top_pts_x:
                    top_pts = (np.array(top_pts_x), np.array(top_pts_y))

            self.plot_results(calc_dist, h_adj, D_total, h_tx_val, h_rx_val, db, hb, loss, top_pts)

        except Exception as e:
            messagebox.showerror("Błąd", f"Wystąpił błąd podczas obliczeń: {e}")

    def plot_results(self, dist_array, h_adj_array, D, h_tx, h_rx, db, hb, loss, top_pts=None):
        self.ax.clear()
        self.ax.fill_between(dist_array, h_adj_array, color='#8d6e63', alpha=0.3, label='Profil terenu ')
        self.ax.plot(dist_array, h_adj_array, color='#5d4037', lw=1.5)
        self.ax.plot([0, D], [h_tx, h_rx], color='blue', linestyle='--', label='Linia widoczności (LOS)')
        self.ax.plot(db, hb, 'ro', markersize=9, label='Ostrze Bullingtona')
        self.ax.vlines(db, ymin=min(h_tx, h_rx)-50, ymax=hb, color='red', linestyles='dotted')
        
        if top_pts is not None:
            self.ax.scatter(top_pts[0], top_pts[1], marker='x', color='yellow', s=100, zorder=5, label='Wykryte 4 szczyty')

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