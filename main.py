"""
LitePDF - Lightweight PDF Reader & Editor
Stack: Python + PyMuPDF (fitz) + tkinter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz  # PyMuPDF
import os
import sys
from PIL import Image, ImageTk
import io
import threading

# ─── Constants ───────────────────────────────────────────────────────────────
APP_NAME   = "LitePDF"
APP_VER    = "1.0.0"
ZOOM_STEPS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
BG         = "#1e1e2e"
SIDEBAR_BG = "#181825"
ACCENT     = "#cba6f7"
FG         = "#cdd6f4"
BTN_BG     = "#313244"
BTN_HOV    = "#45475a"
CANVAS_BG  = "#11111b"

# ─── App ─────────────────────────────────────────────────────────────────────
class LitePDF(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1200x800")
        self.minsize(900, 600)
        self.configure(bg=BG)

        # State
        self.doc          = None
        self.doc_path     = None
        self.current_page = 0
        self.zoom_idx     = 2          # 1.0×
        self.rotation     = 0
        self.photo_cache  = {}         # page_no → PhotoImage
        self._render_lock = threading.Lock()
        self.annotations  = {}         # page_no → list[dict]
        self.highlight_mode = False
        self.text_mode      = False

        self._build_ui()
        self._bind_shortcuts()
        self._update_ui_state()

    # ── UI Construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()
        main = tk.Frame(self, bg=BG)
        main.pack(fill=tk.BOTH, expand=True)
        self._build_sidebar(main)
        self._build_viewer(main)
        self._build_statusbar()

    def _build_menu(self):
        mb = tk.Menu(self, bg=SIDEBAR_BG, fg=FG, activebackground=ACCENT,
                     activeforeground=BG, tearoff=False)
        self.config(menu=mb)

        file_m = tk.Menu(mb, tearoff=False, bg=SIDEBAR_BG, fg=FG,
                         activebackground=ACCENT, activeforeground=BG)
        file_m.add_command(label="Open…          Ctrl+O", command=self.open_file)
        file_m.add_command(label="Save Copy…     Ctrl+S", command=self.save_copy)
        file_m.add_separator()
        file_m.add_command(label="Merge PDFs…",           command=self.merge_pdfs)
        file_m.add_command(label="Split PDF…",             command=self.split_pdf)
        file_m.add_separator()
        file_m.add_command(label="Exit            Alt+F4", command=self.quit)
        mb.add_cascade(label="File", menu=file_m)

        edit_m = tk.Menu(mb, tearoff=False, bg=SIDEBAR_BG, fg=FG,
                         activebackground=ACCENT, activeforeground=BG)
        edit_m.add_command(label="Add Text Annotation", command=self.toggle_text_mode)
        edit_m.add_command(label="Rotate Page CW  →",  command=lambda: self.rotate(90))
        edit_m.add_command(label="Rotate Page CCW ←",  command=lambda: self.rotate(-90))
        edit_m.add_separator()
        edit_m.add_command(label="Extract Text…", command=self.extract_text)
        edit_m.add_command(label="Password Protect…", command=self.password_protect)
        mb.add_cascade(label="Edit", menu=edit_m)

        view_m = tk.Menu(mb, tearoff=False, bg=SIDEBAR_BG, fg=FG,
                         activebackground=ACCENT, activeforeground=BG)
        view_m.add_command(label="Zoom In   Ctrl++", command=self.zoom_in)
        view_m.add_command(label="Zoom Out  Ctrl+-", command=self.zoom_out)
        view_m.add_command(label="Fit Width  Ctrl+0", command=self.zoom_fit)
        view_m.add_separator()
        view_m.add_command(label="Toggle Sidebar  F9", command=self.toggle_sidebar)
        mb.add_cascade(label="View", menu=view_m)

        help_m = tk.Menu(mb, tearoff=False, bg=SIDEBAR_BG, fg=FG,
                         activebackground=ACCENT, activeforeground=BG)
        help_m.add_command(label=f"About {APP_NAME}", command=self.show_about)
        mb.add_cascade(label="Help", menu=help_m)

    def _build_toolbar(self):
        tb = tk.Frame(self, bg=SIDEBAR_BG, pady=4)
        tb.pack(fill=tk.X, side=tk.TOP)

        def btn(parent, text, cmd, tooltip=""):
            b = tk.Button(parent, text=text, command=cmd,
                          bg=BTN_BG, fg=FG, relief=tk.FLAT,
                          padx=10, pady=4, font=("Segoe UI", 9),
                          activebackground=BTN_HOV, activeforeground=FG,
                          cursor="hand2")
            b.pack(side=tk.LEFT, padx=2)
            return b

        btn(tb, "📂 Open",    self.open_file)
        btn(tb, "💾 Save",    self.save_copy)
        tk.Frame(tb, bg=SIDEBAR_BG, width=1, height=28).pack(side=tk.LEFT, padx=6)
        btn(tb, "◀◀ First",  self.go_first)
        btn(tb, "◀ Prev",    self.prev_page)

        # Page entry
        self.page_var = tk.StringVar(value="1")
        self.page_entry = tk.Entry(tb, textvariable=self.page_var, width=4,
                                   bg=BTN_BG, fg=FG, insertbackground=FG,
                                   relief=tk.FLAT, font=("Segoe UI", 9),
                                   justify=tk.CENTER)
        self.page_entry.pack(side=tk.LEFT, padx=2)
        self.page_entry.bind("<Return>", self.jump_to_page)
        self.total_lbl = tk.Label(tb, text="/ —", bg=SIDEBAR_BG, fg=FG,
                                  font=("Segoe UI", 9))
        self.total_lbl.pack(side=tk.LEFT)

        btn(tb, "Next ▶",    self.next_page)
        btn(tb, "Last ▶▶",   self.go_last)
        tk.Frame(tb, bg=SIDEBAR_BG, width=1, height=28).pack(side=tk.LEFT, padx=6)

        btn(tb, "🔍+",       self.zoom_in)
        self.zoom_lbl = tk.Label(tb, text="100%", width=5, bg=SIDEBAR_BG, fg=ACCENT,
                                 font=("Segoe UI", 9, "bold"))
        self.zoom_lbl.pack(side=tk.LEFT, padx=2)
        btn(tb, "🔍−",       self.zoom_out)
        btn(tb, "↔ Fit",    self.zoom_fit)
        tk.Frame(tb, bg=SIDEBAR_BG, width=1, height=28).pack(side=tk.LEFT, padx=6)

        btn(tb, "↻ CW",     lambda: self.rotate(90))
        btn(tb, "↺ CCW",    lambda: self.rotate(-90))
        tk.Frame(tb, bg=SIDEBAR_BG, width=1, height=28).pack(side=tk.LEFT, padx=6)

        self.txt_btn = btn(tb, "✏ Text",    self.toggle_text_mode)
        btn(tb, "📄 Extract", self.extract_text)

    def _build_sidebar(self, parent):
        self.sidebar_frame = tk.Frame(parent, bg=SIDEBAR_BG, width=170)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar_frame.pack_propagate(False)

        tk.Label(self.sidebar_frame, text="PAGES", bg=SIDEBAR_BG, fg=ACCENT,
                 font=("Segoe UI", 8, "bold"), pady=8).pack()

        # Thumbnail listbox
        self.thumb_list = tk.Listbox(self.sidebar_frame, bg=SIDEBAR_BG, fg=FG,
                                     selectbackground=ACCENT, selectforeground=BG,
                                     relief=tk.FLAT, font=("Segoe UI", 9),
                                     activestyle="none", cursor="hand2",
                                     highlightthickness=0)
        self.thumb_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.thumb_list.bind("<<ListboxSelect>>", self.on_thumb_select)

    def _build_viewer(self, parent):
        viewer = tk.Frame(parent, bg=BG)
        viewer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Canvas + scrollbars
        self.canvas = tk.Canvas(viewer, bg=CANVAS_BG, highlightthickness=0,
                                cursor="arrow")
        vscroll = ttk.Scrollbar(viewer, orient=tk.VERTICAL,   command=self.canvas.yview)
        hscroll = ttk.Scrollbar(viewer, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        vscroll.pack(side=tk.RIGHT,  fill=tk.Y)
        hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Welcome label
        self.welcome_lbl = tk.Label(self.canvas,
            text="📄  Drop a PDF here or use  File → Open",
            bg=CANVAS_BG, fg="#585b70",
            font=("Segoe UI", 15))
        self.canvas.create_window(600, 350, window=self.welcome_lbl, tags="welcome")

        self.canvas.bind("<Configure>",          self._on_canvas_resize)
        self.canvas.bind("<MouseWheel>",          self._on_mousewheel)
        self.canvas.bind("<Button-1>",            self._on_canvas_click)
        self.canvas.bind("<ButtonPress-2>",       self._pan_start)
        self.canvas.bind("<B2-Motion>",           self._pan_move)

        # Drag-and-drop
        try:
            self.drop_target_register = None
            self.canvas.bind("<Drop>", self._on_drop)
        except Exception:
            pass

    def _build_statusbar(self):
        sb = tk.Frame(self, bg=SIDEBAR_BG, pady=3)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="Ready — open a PDF to begin")
        tk.Label(sb, textvariable=self.status_var, bg=SIDEBAR_BG, fg=FG,
                 font=("Segoe UI", 8), anchor=tk.W, padx=10).pack(side=tk.LEFT)
        self.info_var = tk.StringVar()
        tk.Label(sb, textvariable=self.info_var, bg=SIDEBAR_BG, fg="#6c7086",
                 font=("Segoe UI", 8), anchor=tk.E, padx=10).pack(side=tk.RIGHT)

    # ── Keyboard shortcuts ────────────────────────────────────────────────────
    def _bind_shortcuts(self):
        self.bind("<Control-o>",       lambda e: self.open_file())
        self.bind("<Control-s>",       lambda e: self.save_copy())
        self.bind("<Control-equal>",   lambda e: self.zoom_in())
        self.bind("<Control-minus>",   lambda e: self.zoom_out())
        self.bind("<Control-0>",       lambda e: self.zoom_fit())
        self.bind("<Right>",           lambda e: self.next_page())
        self.bind("<Left>",            lambda e: self.prev_page())
        self.bind("<Home>",            lambda e: self.go_first())
        self.bind("<End>",             lambda e: self.go_last())
        self.bind("<F9>",              lambda e: self.toggle_sidebar())

    # ── File operations ───────────────────────────────────────────────────────
    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open PDF", filetypes=[("PDF files", "*.pdf"), ("All", "*.*")])
        if path:
            self._load_pdf(path)

    def _load_pdf(self, path):
        try:
            self.doc      = fitz.open(path)
            self.doc_path = path
            self.current_page = 0
            self.rotation = 0
            self.photo_cache.clear()
            self.annotations.clear()
            self._populate_sidebar()
            self._render_page()
            self._update_ui_state()
            name = os.path.basename(path)
            self.title(f"{name} — {APP_NAME}")
            self.status_var.set(f"Opened: {name}")
            self.info_var.set(
                f"{len(self.doc)} pages  •  {os.path.getsize(path)//1024} KB")
            # Hide welcome label
            self.canvas.itemconfigure("welcome", state="hidden")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open PDF:\n{e}")

    def save_copy(self):
        if not self.doc:
            return
        path = filedialog.asksaveasfilename(
            title="Save PDF Copy",
            defaultextension=".pdf",
            initialfile=os.path.basename(self.doc_path or "copy.pdf"),
            filetypes=[("PDF files", "*.pdf")])
        if path:
            try:
                self.doc.save(path, garbage=4, deflate=True)
                self.status_var.set(f"Saved: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save:\n{e}")

    def merge_pdfs(self):
        files = filedialog.askopenfilenames(
            title="Select PDFs to Merge",
            filetypes=[("PDF files", "*.pdf")])
        if not files:
            return
        out = filedialog.asksaveasfilename(
            title="Save Merged PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")])
        if not out:
            return
        try:
            writer = fitz.open()
            for f in files:
                writer.insert_pdf(fitz.open(f))
            writer.save(out, garbage=4, deflate=True)
            if messagebox.askyesno("Done", f"Merged {len(files)} PDFs.\nOpen result?"):
                self._load_pdf(out)
        except Exception as e:
            messagebox.showerror("Error", f"Merge failed:\n{e}")

    def split_pdf(self):
        if not self.doc:
            messagebox.showinfo("Split PDF", "Open a PDF first.")
            return
        folder = filedialog.askdirectory(title="Select Output Folder")
        if not folder:
            return
        try:
            base = os.path.splitext(os.path.basename(self.doc_path))[0]
            for i, page in enumerate(self.doc):
                out = fitz.open()
                out.insert_pdf(self.doc, from_page=i, to_page=i)
                out.save(os.path.join(folder, f"{base}_page{i+1:03d}.pdf"))
            messagebox.showinfo("Done", f"Split into {len(self.doc)} files in:\n{folder}")
        except Exception as e:
            messagebox.showerror("Error", f"Split failed:\n{e}")

    def extract_text(self):
        if not self.doc:
            return
        page = self.doc[self.current_page]
        text = page.get_text("text")
        win  = tk.Toplevel(self)
        win.title(f"Text — Page {self.current_page+1}")
        win.geometry("640x500")
        win.configure(bg=BG)
        txt = tk.Text(win, bg=SIDEBAR_BG, fg=FG, font=("Consolas", 10),
                      wrap=tk.WORD, relief=tk.FLAT, padx=10, pady=10)
        sb  = ttk.Scrollbar(win, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, text if text.strip() else "[No selectable text on this page]")
        txt.config(state=tk.DISABLED)

    def password_protect(self):
        if not self.doc:
            return
        pwd = simpledialog.askstring("Password", "Enter password:", show="*")
        if not pwd:
            return
        path = filedialog.asksaveasfilename(
            title="Save Encrypted PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        try:
            self.doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256,
                          user_pw=pwd, owner_pw=pwd)
            messagebox.showinfo("Done", "PDF saved with password protection.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not encrypt:\n{e}")

    # ── Navigation ────────────────────────────────────────────────────────────
    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self._render_page()
            self._update_ui_state()

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self._render_page()
            self._update_ui_state()

    def go_first(self):
        if self.doc:
            self.current_page = 0
            self._render_page()
            self._update_ui_state()

    def go_last(self):
        if self.doc:
            self.current_page = len(self.doc) - 1
            self._render_page()
            self._update_ui_state()

    def jump_to_page(self, _=None):
        if not self.doc:
            return
        try:
            n = int(self.page_var.get()) - 1
            n = max(0, min(n, len(self.doc)-1))
            self.current_page = n
            self._render_page()
            self._update_ui_state()
        except ValueError:
            self._update_ui_state()

    # ── Zoom ──────────────────────────────────────────────────────────────────
    @property
    def zoom(self):
        return ZOOM_STEPS[self.zoom_idx]

    def zoom_in(self):
        if self.zoom_idx < len(ZOOM_STEPS) - 1:
            self.zoom_idx += 1
            self._render_page()
            self._update_ui_state()

    def zoom_out(self):
        if self.zoom_idx > 0:
            self.zoom_idx -= 1
            self._render_page()
            self._update_ui_state()

    def zoom_fit(self):
        if not self.doc:
            return
        page  = self.doc[self.current_page]
        rect  = page.rect
        w_fit = self.canvas.winfo_width()  / rect.width
        best  = min(ZOOM_STEPS, key=lambda z: abs(z - w_fit * 0.95))
        self.zoom_idx = ZOOM_STEPS.index(best)
        self._render_page()
        self._update_ui_state()

    # ── Rotate ────────────────────────────────────────────────────────────────
    def rotate(self, deg):
        if not self.doc:
            return
        self.rotation = (self.rotation + deg) % 360
        self.photo_cache.clear()
        self._render_page()

    # ── Annotation ────────────────────────────────────────────────────────────
    def toggle_text_mode(self):
        self.text_mode = not self.text_mode
        self.highlight_mode = False
        color = ACCENT if self.text_mode else BTN_BG
        self.txt_btn.config(bg=color)
        self.canvas.config(cursor="xterm" if self.text_mode else "arrow")
        state = "ON" if self.text_mode else "OFF"
        self.status_var.set(f"Text annotation mode: {state} — click on the page to place text")

    def _on_canvas_click(self, event):
        if not self.doc or not self.text_mode:
            return
        text = simpledialog.askstring("Add Text", "Enter annotation text:")
        if not text:
            return
        page   = self.doc[self.current_page]
        zoom_m = fitz.Matrix(self.zoom, self.zoom).prerotate(self.rotation)
        # Convert canvas coords → PDF coords
        x_pdf = event.x / self.zoom
        y_pdf = event.y / self.zoom
        rect  = fitz.Rect(x_pdf-5, y_pdf-10, x_pdf+200, y_pdf+5)
        page.insert_text((x_pdf, y_pdf), text, fontsize=12, color=(0.8, 0.2, 0.8))
        self.photo_cache.pop(self.current_page, None)
        self._render_page()
        self.status_var.set(f"Annotation added to page {self.current_page+1}")

    # ── Rendering ─────────────────────────────────────────────────────────────
    def _render_page(self):
        if not self.doc:
            return
        key = (self.current_page, self.zoom_idx, self.rotation)
        if key not in self.photo_cache:
            page   = self.doc[self.current_page]
            matrix = fitz.Matrix(self.zoom, self.zoom).prerotate(self.rotation)
            pix    = page.get_pixmap(matrix=matrix, alpha=False)
            img    = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.photo_cache[key] = ImageTk.PhotoImage(img)

        photo = self.photo_cache[key]
        self.canvas.delete("page")
        cw = self.canvas.winfo_width()
        x  = max(photo.width() // 2, cw // 2)
        self.canvas.create_image(x, 10, image=photo, anchor=tk.N, tags="page")
        self.canvas.config(scrollregion=(0, 0,
                           max(photo.width(), cw),
                           photo.height() + 20))
        self.canvas.yview_moveto(0)

        # Sync sidebar
        self.thumb_list.selection_clear(0, tk.END)
        self.thumb_list.selection_set(self.current_page)
        self.thumb_list.see(self.current_page)

    def _on_canvas_resize(self, _=None):
        if self.doc:
            self.photo_cache.clear()
            self._render_page()

    def _on_mousewheel(self, event):
        if event.state & 0x4:            # Ctrl held → zoom
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _pan_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _pan_move(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_drop(self, event):
        path = event.data.strip("{}")
        if path.lower().endswith(".pdf"):
            self._load_pdf(path)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _populate_sidebar(self):
        self.thumb_list.delete(0, tk.END)
        for i in range(len(self.doc)):
            self.thumb_list.insert(tk.END, f"  Page {i+1:>4}")

    def on_thumb_select(self, _=None):
        sel = self.thumb_list.curselection()
        if sel:
            self.current_page = sel[0]
            self._render_page()
            self._update_ui_state()

    def toggle_sidebar(self):
        if self.sidebar_frame.winfo_ismapped():
            self.sidebar_frame.pack_forget()
        else:
            self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, before=self.canvas.master)

    # ── UI state sync ─────────────────────────────────────────────────────────
    def _update_ui_state(self):
        if self.doc:
            n = len(self.doc)
            self.page_var.set(str(self.current_page + 1))
            self.total_lbl.config(text=f"/ {n}")
            self.zoom_lbl.config(text=f"{int(self.zoom*100)}%")
        else:
            self.page_var.set("—")
            self.total_lbl.config(text="/ —")
            self.zoom_lbl.config(text="—")

    # ── About ─────────────────────────────────────────────────────────────────
    def show_about(self):
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} v{APP_VER}\n\n"
            "Lightweight PDF reader & editor\n"
            "Built with Python, PyMuPDF, and tkinter\n\n"
            "Features:\n"
            "  • View PDF with zoom, pan, rotate\n"
            "  • Page navigation & sidebar\n"
            "  • Text extraction\n"
            "  • Add text annotations\n"
            "  • Merge & split PDFs\n"
            "  • Password protection\n"
            "  • Save copy\n\n"
            "Keyboard shortcuts:\n"
            "  Ctrl+O    Open\n"
            "  Ctrl+S    Save copy\n"
            "  ←/→       Navigate pages\n"
            "  Ctrl++/-  Zoom in/out\n"
            "  Ctrl+0    Fit width\n"
            "  F9        Toggle sidebar"
        )


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = LitePDF()
    # Open file passed as argument (e.g. from Windows shell association)
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.after(100, lambda: app._load_pdf(sys.argv[1]))
    app.mainloop()
