import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pydicom
import os

class DICOMViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("DICOM 画像ビューア")
        self.root.geometry("1400x800")
        
        self.dicom_data = None
        self.volume = None
        self.current_slice_axial = 0
        self.current_slice_other = 0
        self.window_width = 400
        self.window_level = 40
        self.view_mode = "Sagittal"         
        self.setup_ui()
        self.show_welcome_message()
        self.root.after(500, self.load_dicom)
        
    def setup_ui(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="DICOMファイルを開く", command=self.load_dicom, accelerator="Ctrl+O")
        file_menu.add_command(label="複数のDICOMファイルを開く", command=self.load_multiple_dicom, accelerator="Ctrl+Shift+O")
        file_menu.add_command(label="DICOMフォルダを開く", command=self.load_dicom_folder, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit, accelerator="Ctrl+Q")
        self.root.bind('<Control-o>', lambda e: self.load_dicom())
        self.root.bind('<Control-Shift-O>', lambda e: self.load_multiple_dicom())
        self.root.bind('<Control-d>', lambda e: self.load_dicom_folder())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        toolbar = ttk.Frame(main_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        open_btn = ttk.Button(toolbar, text="📁 ファイルを開く", command=self.load_dicom)
        open_btn.pack(side=tk.LEFT, padx=5)
        open_multiple_btn = ttk.Button(toolbar, text="📂 複数ファイルを開く", command=self.load_multiple_dicom)
        open_multiple_btn.pack(side=tk.LEFT, padx=5)
        open_folder_btn = ttk.Button(toolbar, text="📁 フォルダを開く", command=self.load_dicom_folder)
        open_folder_btn.pack(side=tk.LEFT, padx=5)
        self.file_label = ttk.Label(toolbar, text="ファイル: 未選択", foreground="gray")
        self.file_label.pack(side=tk.LEFT, padx=20)
        image_frame = ttk.Frame(main_frame)
        image_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        self.fig = Figure(figsize=(14, 6), facecolor='#2b2b2b')
        self.ax1 = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)
        self.ax1.set_facecolor('#1a1a1a')
        self.ax2.set_facecolor('#1a1a1a')
        self.ax1.axis('off')
        self.ax2.axis('off')
        self.canvas = FigureCanvasTkAgg(self.fig, master=image_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.LabelFrame(main_frame, text="画像調整", padding="10")
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        ttk.Label(control_frame, text="Axial スライス:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.slice_axial_var = tk.IntVar(value=0)
        self.slice_axial_slider = ttk.Scale(
            control_frame, from_=0, to=0, 
            variable=self.slice_axial_var, 
            orient=tk.HORIZONTAL,
            command=self.update_display
        )
        self.slice_axial_slider.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.slice_axial_label = ttk.Label(control_frame, text="0 / 0")
        self.slice_axial_label.grid(row=0, column=2, padx=5)
        ttk.Label(control_frame, text="表示モード:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.view_mode_var = tk.StringVar(value="Sagittal")
        view_mode_combo = ttk.Combobox(
            control_frame, 
            textvariable=self.view_mode_var,
            values=["Sagittal", "Coronal"],
            state="readonly",
            width=15
        )
        view_mode_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        view_mode_combo.bind("<<ComboboxSelected>>", self.change_view_mode)
        ttk.Label(control_frame, text="スライス:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.slice_other_var = tk.IntVar(value=0)
        self.slice_other_slider = ttk.Scale(
            control_frame, from_=0, to=0,
            variable=self.slice_other_var,
            orient=tk.HORIZONTAL,
            command=self.update_display
        )
        self.slice_other_slider.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        self.slice_other_label = ttk.Label(control_frame, text="0 / 0")
        self.slice_other_label.grid(row=2, column=2, padx=5)
        ttk.Label(control_frame, text="Window Width:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.ww_var = tk.IntVar(value=400)
        self.ww_slider = ttk.Scale(
            control_frame, from_=1, to=2000,
            variable=self.ww_var,
            orient=tk.HORIZONTAL,
            command=self.update_display
        )
        self.ww_slider.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.ww_label = ttk.Label(control_frame, text="400")
        self.ww_label.grid(row=3, column=2, padx=5)
        ttk.Label(control_frame, text="Window Level:").grid(row=4, column=0, sticky=tk.W, padx=5)
        self.wl_var = tk.IntVar(value=40)
        self.wl_slider = ttk.Scale(
            control_frame, from_=-1000, to=1000,
            variable=self.wl_var,
            orient=tk.HORIZONTAL,
            command=self.update_display
        )
        self.wl_slider.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=5)
        self.wl_label = ttk.Label(control_frame, text="40")
        self.wl_label.grid(row=4, column=2, padx=5)
        control_frame.columnconfigure(1, weight=1)

    def show_welcome_message(self):
        self.ax1.clear()
        self.ax2.clear()
        self.ax1.text(0.5, 0.5, 'DICOM画像ビューア\n\nファイルを開いてください', 
                    ha='center', va='center', color='white', fontsize=16,
                    transform=self.ax1.transAxes)
        self.ax1.set_facecolor('#1a1a1a')
        self.ax1.axis('off')
        self.ax2.text(0.5, 0.5, 'メニューバーから\n「ファイル」→「DICOMファイルを開く」\nを選択', 
                    ha='center', va='center', color='white', fontsize=14,
                    transform=self.ax2.transAxes)
        self.ax2.set_facecolor('#1a1a1a')
        self.ax2.axis('off')
        self.canvas.draw()
        
    def load_dicom(self):
        """DICOMファイルを読み込む"""
        file_path = filedialog.askopenfilename(
            title="DICOMファイルを選択",
            filetypes=[("DICOM files", "*.dcm"), ("All files", "*.*")],
            initialdir=os.path.dirname(os.path.abspath(__file__))
        )
        if not file_path:
            if self.volume is None:
                self.show_welcome_message()
            return
        try:
            self.dicom_data = pydicom.dcmread(file_path)
            pixel_array = self.dicom_data.pixel_array
            if len(pixel_array.shape) == 2:
                self.volume = np.stack([pixel_array] * 10, axis=0)
                messagebox.showinfo("情報", "単一スライスのDICOMファイルです。\n表示のため10枚に複製しました。")
            else:
                self.volume = pixel_array
            self.volume = self.volume.astype(np.float32)
            self.slice_axial_slider.config(to=self.volume.shape[0] - 1)
            self.current_slice_axial = self.volume.shape[0] // 2
            self.slice_axial_var.set(self.current_slice_axial)
            self.update_slice_range()
            if hasattr(self.dicom_data, 'WindowWidth') and hasattr(self.dicom_data, 'WindowCenter'):
                self.window_width = int(self.dicom_data.WindowWidth)
                self.window_level = int(self.dicom_data.WindowCenter)
            else:
                self.window_width = int(np.ptp(self.volume))
                self.window_level = int(np.mean(self.volume))
            self.ww_var.set(self.window_width)
            self.wl_var.set(self.window_level)
            self.update_display()
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"ファイル: {filename}", foreground="green")
            messagebox.showinfo("成功", f"DICOMファイルを読み込みました\n形状: {self.volume.shape}")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{str(e)}")
    
    def load_multiple_dicom(self):
        """複数のDICOMファイルを読み込む"""
        file_paths = filedialog.askopenfilenames(
            title="複数のDICOMファイルを選択",
            filetypes=[("DICOM files", "*.dcm"), ("All files", "*.*")],
            initialdir=os.path.dirname(os.path.abspath(__file__))
        )
        if not file_paths:
            if self.volume is None:
                self.show_welcome_message()
            return
        self.load_dicom_files(file_paths)

    def load_dicom_folder(self):
        """フォルダ内のすべてのDICOMファイルを読み込む"""
        folder_path = filedialog.askdirectory(
            title="DICOMファイルが含まれるフォルダを選択",
            initialdir=os.path.dirname(os.path.abspath(__file__))
        )
        if not folder_path:
            if self.volume is None:
                self.show_welcome_message()
            return
        dcm_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.dcm'):
                    dcm_files.append(os.path.join(root, file))
        if not dcm_files:
            messagebox.showwarning("警告", "フォルダ内にDICOMファイルが見つかりませんでした")
            return
        self.load_dicom_files(dcm_files)
    def load_dicom_files(self, file_paths):
        try:
            progress_window = tk.Toplevel(self.root)
            progress_window.title("読み込み中...")
            progress_window.geometry("400x100")
            progress_window.transient(self.root)
            progress_window.grab_set()
            progress_label = ttk.Label(progress_window, text="DICOMファイルを読み込んでいます...")
            progress_label.pack(pady=10)
            progress_bar = ttk.Progressbar(progress_window, length=300, mode='determinate')
            progress_bar.pack(pady=10)
            dicom_slices = []
            total_files = len(file_paths)
            
            for idx, file_path in enumerate(file_paths):
                try:
                    ds = pydicom.dcmread(file_path)
                    if hasattr(ds, 'ImagePositionPatient'):
                        slice_location = ds.ImagePositionPatient[2]
                    elif hasattr(ds, 'SliceLocation'):
                        slice_location = ds.SliceLocation
                    else:
                        slice_location = idx
                    dicom_slices.append((slice_location, ds))
                    progress_bar['value'] = (idx + 1) / total_files * 100
                    progress_window.update()
                except Exception as e:
                    print(f"警告: {file_path} の読み込みに失敗しました: {e}")
                    continue
            if not dicom_slices:
                progress_window.destroy()
                messagebox.showerror("エラー", "有効なDICOMファイルが見つかりませんでした")
                return
            dicom_slices.sort(key=lambda x: x[0])
            
            slices_data = []
            for _, ds in dicom_slices:
                pixel_array = ds.pixel_array
                if len(pixel_array.shape) == 2:
                    slices_data.append(pixel_array)
                elif len(pixel_array.shape) == 3:
                    for i in range(pixel_array.shape[0]):
                        slices_data.append(pixel_array[i])
            
            self.volume = np.stack(slices_data, axis=0).astype(np.float32)
            self.dicom_data = dicom_slices[0][1]  
            progress_window.destroy()
            self.slice_axial_slider.config(to=self.volume.shape[0] - 1)
            self.current_slice_axial = self.volume.shape[0] // 2
            self.slice_axial_var.set(self.current_slice_axial)
            self.update_slice_range()
            if hasattr(self.dicom_data, 'WindowWidth') and hasattr(self.dicom_data, 'WindowCenter'):
                ww = self.dicom_data.WindowWidth
                wl = self.dicom_data.WindowCenter
                self.window_width = int(ww[0] if isinstance(ww, (list, tuple)) else ww)
                self.window_level = int(wl[0] if isinstance(wl, (list, tuple)) else wl)
            else:
                self.window_width = int(np.ptp(self.volume))
                self.window_level = int(np.mean(self.volume))
            self.ww_var.set(self.window_width)
            self.wl_var.set(self.window_level)
            self.update_display()
            if len(file_paths) == 1:
                filename = os.path.basename(file_paths[0])
            else:
                filename = f"{len(file_paths)}個のファイル ({len(slices_data)}スライス)"
            self.file_label.config(text=f"ファイル: {filename}", foreground="green")
            
            messagebox.showinfo("成功", 
                            f"DICOMファイルを読み込みました\n"
                            f"ファイル数: {len(file_paths)}\n"
                            f"スライス数: {len(slices_data)}\n"
                            f"形状: {self.volume.shape}")
        except Exception as e:
            if 'progress_window' in locals():
                progress_window.destroy()
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{str(e)}")
    
    def update_slice_range(self):
        """スライス範囲を更新"""
        if self.volume is None:
            return
        
        if self.view_mode == "Sagittal":
            max_slice = self.volume.shape[2] - 1
            self.current_slice_other = min(self.current_slice_other, max_slice)
        else:  
            max_slice = self.volume.shape[1] - 1
            self.current_slice_other = min(self.current_slice_other, max_slice)
        
        self.slice_other_slider.config(to=max_slice)
        self.slice_other_var.set(self.current_slice_other)
    
    def change_view_mode(self, event=None):
        self.view_mode = self.view_mode_var.get()
        self.update_slice_range()
        self.update_display()
    
    def apply_window(self, image, ww, wl):
        min_value = wl - ww / 2
        max_value = wl + ww / 2
        
        windowed = np.clip(image, min_value, max_value)
        windowed = (windowed - min_value) / (max_value - min_value) * 255
        
        return windowed.astype(np.uint8)
    
    def update_display(self, event=None):
        if self.volume is None:
            return
        self.current_slice_axial = int(self.slice_axial_var.get())
        self.current_slice_other = int(self.slice_other_var.get())
        self.window_width = int(self.ww_var.get())
        self.window_level = int(self.wl_var.get())
        self.slice_axial_label.config(
            text=f"{self.current_slice_axial} / {self.volume.shape[0] - 1}"
        )
        self.slice_other_label.config(
            text=f"{self.current_slice_other} / {self.slice_other_slider.cget('to')}"
        )
        self.ww_label.config(text=str(self.window_width))
        self.wl_label.config(text=str(self.window_level))
        axial_img = self.volume[self.current_slice_axial, :, :]
        axial_windowed = self.apply_window(axial_img, self.window_width, self.window_level)
        if self.view_mode == "Sagittal":
            other_img = self.volume[:, :, self.current_slice_other]
            other_windowed = self.apply_window(other_img, self.window_width, self.window_level)
        else: 
            other_img = self.volume[:, self.current_slice_other, :]
            other_windowed = self.apply_window(other_img, self.window_width, self.window_level)
        self.ax1.clear()
        self.ax2.clear()
        self.ax1.imshow(axial_windowed, cmap='gray', aspect='auto')
        self.ax1.set_title(f'Axial (Slice {self.current_slice_axial})', 
                        color='white', fontsize=12, fontweight='bold')
        self.ax1.axis('off')
        if self.view_mode == "Sagittal":
            self.ax1.axvline(x=self.current_slice_other, color='cyan', linewidth=2, linestyle='--', alpha=0.8)
        else:  
            self.ax1.axhline(y=self.current_slice_other, color='yellow', linewidth=2, linestyle='--', alpha=0.8)
        self.ax2.imshow(other_windowed, cmap='gray', aspect='auto')
        self.ax2.set_title(f'{self.view_mode} (Slice {self.current_slice_other})',
                        color='white', fontsize=12, fontweight='bold')
        self.ax2.axis('off')
        self.ax1.set_facecolor('#1a1a1a')
        self.ax2.set_facecolor('#1a1a1a')
        self.fig.tight_layout()
        self.canvas.draw()

def main():
    root = tk.Tk()
    app = DICOMViewer(root)
    root.mainloop()
    
if __name__ == "__main__":
    main()
